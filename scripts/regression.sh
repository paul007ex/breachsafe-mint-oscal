#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# Black-box CLI regression harness — run during PR.
#
# Exercises every mint-oscal CLI parameter and exit path, plus a regression guard for
# every bug fixed to date (#62 open-vocab / #64 zero-finding / #67 legacy-TLS-string /
# #68 RSA key transport / never-raises / determinism / honest-failure). No pytest, no
# mocks: it drives the real console entry point against real + adversarial inputs and
# asserts exit codes and output invariants.
#
# Usage:
#   scripts/regression.sh                 # installed `mint-oscal`, else `python -m mint_oscal.cli`
#   MINT="/path/to/mint-oscal" scripts/regression.sh
#
# Exit 0 iff every check passes; non-zero (= number of failures) otherwise.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EX="$ROOT/examples"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- resolve the CLI under test -------------------------------------------------------
if [ -n "${MINT:-}" ]; then
  :
elif command -v mint-oscal >/dev/null 2>&1; then
  MINT="mint-oscal"
else
  MINT="python3 -m mint_oscal.cli"
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi
PY="${PYTHON:-python3}"

pass=0
fail=0
_ok() { pass=$((pass + 1)); printf "  \033[32mPASS\033[0m  %s\n" "$1"; }
_no() { fail=$((fail + 1)); printf "  \033[31mFAIL\033[0m  %s\n" "$1"; }

# expect_exit WANT "desc" -- <cli args...>
expect_exit() {
  local want="$1" desc="$2"; shift 3   # drop WANT, desc, the literal `--`
  $MINT "$@" >"$TMP/o" 2>"$TMP/e"
  local got=$?
  if [ "$got" -eq "$want" ]; then _ok "$desc (exit $got)"
  else _no "$desc (want $want, got $got)"; sed 's/^/        /' "$TMP/e" | head -3; fi
}

# stdout_has "needle" "desc" -- <cli args...>
stdout_has() {
  local needle="$1" desc="$2"; shift 3
  if $MINT "$@" 2>/dev/null | grep -qF "$needle"; then _ok "$desc"
  else _no "$desc (stdout missing: $needle)"; fi
}

# stdout_valid_json "desc" -- <cli args...>
stdout_valid_json() {
  local desc="$1"; shift 2
  if $MINT "$@" 2>/dev/null | "$PY" -m json.tool >/dev/null 2>&1; then _ok "$desc"
  else _no "$desc (stdout not valid JSON)"; fi
}

# stderr_has / stderr_lacks "needle" "desc" -- <cli args...>
stderr_has() {
  local needle="$1" desc="$2"; shift 3
  $MINT "$@" >/dev/null 2>"$TMP/e"
  if grep -qF "$needle" "$TMP/e"; then _ok "$desc"; else _no "$desc (stderr missing: $needle)"; fi
}
stderr_lacks() {
  local needle="$1" desc="$2"; shift 3
  $MINT "$@" >/dev/null 2>"$TMP/e"
  if grep -qF "$needle" "$TMP/e"; then _no "$desc (stderr unexpectedly has: $needle)"; else _ok "$desc"; fi
}
# stderr_ndjson "desc" -- <cli args...>  (every non-blank STDERR line is valid JSON)
stderr_ndjson() {
  local desc="$1"; shift 2
  $MINT "$@" >/dev/null 2>"$TMP/e"
  if [ -s "$TMP/e" ] && "$PY" -c 'import sys,json;[json.loads(l) for l in sys.stdin if l.strip()]' <"$TMP/e" 2>/dev/null
  then _ok "$desc"; else _no "$desc (stderr not NDJSON)"; fi
}

# _readiness <cbom file> -> "<readiness> <legacy-bool-lowercase> <kex-offered...>"
_readiness() {
  $MINT poam generate --from cbom "$1" 2>/dev/null | "$PY" -c '
import sys, json
p = json.load(sys.stdin)["plan-of-action-and-milestones"]
props = {pr["name"]: pr["value"] for o in p.get("observations", []) for pr in o.get("props", [])}
print(props.get("readiness", "NONE"), str("legacy-protocols" in props).lower(), props.get("kex-offered", "-"))'
}

# readiness_is EXPECT LEGACY(true/false) "desc" <cbom file>
readiness_is() {
  local want="$1" legacy="$2" desc="$3" file="$4" r leg kex
  read -r r leg kex <<<"$(_readiness "$file")"
  if [ "$r" = "$want" ] && [ "$leg" = "$legacy" ]; then _ok "$desc -> $r legacy=$leg kex=$kex"
  else _no "$desc (want $want/$legacy, got $r/$leg kex=$kex)"; fi
}

# ======================================================================================
# fixtures (generated inline; happy-path canonical inputs come from examples/)
# ======================================================================================
cbom() {  # cbom <version> <extra-components-json>
  cat >"$1"
}

# #67: a KEM-only inventory (base = quantum_ready) behind a legacy TLS 1.0 transport.
cbom "$TMP/tlsv10.cbom.json" <<'JSON'
{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,
 "metadata":{"timestamp":"2026-01-01T00:00:00Z","component":{"type":"platform","name":"h:443"}},
 "components":[
  {"type":"cryptographic-asset","name":"MLKEM768","cryptoProperties":{"assetType":"algorithm",
    "algorithmProperties":{"primitive":"kem","nistQuantumSecurityLevel":3}}},
  {"type":"cryptographic-asset","name":"legacy-tls","cryptoProperties":{"assetType":"protocol",
    "protocolProperties":{"type":"tls","version":"TLSv1.0"}}}]}
JSON

# #68: RSA key transport (pke) alongside a safe ML-KEM.
cbom "$TMP/rsa_pke.cbom.json" <<'JSON'
{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,
 "metadata":{"timestamp":"2026-01-01T00:00:00Z","component":{"type":"platform","name":"h:443"}},
 "components":[
  {"type":"cryptographic-asset","name":"RSA","cryptoProperties":{"assetType":"algorithm",
    "algorithmProperties":{"primitive":"pke","nistQuantumSecurityLevel":0}}},
  {"type":"cryptographic-asset","name":"MLKEM768","cryptoProperties":{"assetType":"algorithm",
    "algorithmProperties":{"primitive":"kem","nistQuantumSecurityLevel":3}}}]}
JSON

# honest-failure control: modern KEM-only, no legacy transport -> quantum_ready (not over-flagged).
cbom "$TMP/allsafe.cbom.json" <<'JSON'
{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,
 "metadata":{"timestamp":"2026-01-01T00:00:00Z","component":{"type":"platform","name":"h:443"}},
 "components":[
  {"type":"cryptographic-asset","name":"MLKEM1024","cryptoProperties":{"assetType":"algorithm",
    "algorithmProperties":{"primitive":"kem","nistQuantumSecurityLevel":5}}}]}
JSON

# #64: a clean qureddy scan (zero findings).
cat >"$TMP/empty.scan.json" <<'JSON'
{"schema":"qureddy.scan.v1","target":{"locator":"tls://h:443","scheme":"tls","host":"h","port":443},
 "scan":{"completed_at":"2026-01-01T00:00:00Z"},"findings":[],"evidence":[]}
JSON

# A qureddy-flavoured CBOM (native qureddy: namespace): a hybrid inventory + the producer's
# declared verdict + one evidence record -- to exercise the --extension breachsafe bridge.
cat >"$TMP/hybrid.qureddy.cbom.json" <<'JSON'
{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,
 "metadata":{"timestamp":"2026-01-01T00:00:00Z",
   "component":{"type":"platform","name":"example.com:443"},
   "properties":[
     {"name":"qureddy:scan.readiness","value":"transitional_hybrid"},
     {"name":"qureddy:evidence.00.type","value":"tls.negotiation"},
     {"name":"qureddy:evidence.00.stdout_sha256","value":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}]},
 "components":[
   {"type":"cryptographic-asset","name":"X25519MLKEM768","cryptoProperties":{"assetType":"algorithm","algorithmProperties":{"primitive":"kem","nistQuantumSecurityLevel":3}}},
   {"type":"cryptographic-asset","name":"X25519","cryptoProperties":{"assetType":"algorithm","algorithmProperties":{"primitive":"key-agree","nistQuantumSecurityLevel":0}}}]}
JSON
# same, but the producer over-claims a favorable quantum_ready (honest-failure test)
"$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));[p.__setitem__("value","quantum_ready") for p in d["metadata"]["properties"] if p["name"]=="qureddy:scan.readiness"];json.dump(d,open(sys.argv[2],"w"))' "$TMP/hybrid.qureddy.cbom.json" "$TMP/conflict.qureddy.cbom.json"

echo '{"bomFormat":"NotCycloneDX","specVersion":"1.6"}' >"$TMP/bad.cbom.json"   # wrong bomFormat
echo '{"schema":"qureddy.scan.v1","scan":{}}' >"$TMP/bad.scan.json"            # missing target
printf '{ this is not json ' >"$TMP/notjson.json"

# ======================================================================================
echo
echo "mint-oscal regression harness  (CLI: $MINT)"
echo "======================================================================================"

echo "-- help / version / discovery --"
expect_exit 0 "--version"                        -- --version
stdout_has "BreachSAFE Mint-OSCAL" "--version banner" -- --version
expect_exit 0 "-V"                               -- -V
expect_exit 0 "--help"                           -- --help
expect_exit 0 "-h"                               -- -h
expect_exit 0 "(no args) prints help"            --
# #70: an incomplete invocation keeps STDOUT a pure OSCAL channel (help -> STDERR), exit 0.
$MINT >"$TMP/o" 2>"$TMP/e"; noargs=$?
if [ "$noargs" -eq 0 ] && [ ! -s "$TMP/o" ] && grep -q "usage: mint-oscal" "$TMP/e"; then
  _ok "#70 no-args: help on STDERR, STDOUT empty, exit 0"
else _no "#70 no-args (exit=$noargs, stdout-bytes=$(wc -c <"$TMP/o"|tr -d ' '))"; fi
expect_exit 0 "bare 'help' word"                 -- help
# explicit help request writes to STDOUT (it is the requested output)
if $MINT help 2>/dev/null | grep -q "usage: mint-oscal"; then _ok "explicit 'help' -> STDOUT"
else _no "explicit 'help' not on STDOUT"; fi
expect_exit 0 "poam --help"                      -- poam --help
expect_exit 0 "poam (model, no verb) -> help"    -- poam
expect_exit 0 "poam generate --help"             -- poam generate --help
expect_exit 0 "poam generate -h"                 -- poam generate -h
stdout_has "EXIT CODES:" "generate --help has EXIT CODES section" -- poam generate --help
stdout_has "70" "generate --help documents exit 70" -- poam generate --help
stdout_has "(planned)" "root help labels stub models planned" -- --help

echo "-- happy paths --"
expect_exit 0 "cbom file"                        -- poam generate --from cbom "$EX/example.cbom.json"
stdout_valid_json "cbom -> valid JSON on stdout" -- poam generate --from cbom "$EX/example.cbom.json"
stdout_has "plan-of-action-and-milestones" "cbom -> POA&M root" -- poam generate --from cbom "$EX/example.cbom.json"
expect_exit 0 "qureddy file"                     -- poam generate --from qureddy "$EX/example.scan.json"
expect_exit 0 "--extension breachsafe"           -- poam generate --from cbom "$EX/example.cbom.json" --extension breachsafe
stdout_has "provenance" "extension stamps provenance" -- poam generate --from cbom "$EX/example.cbom.json" --extension breachsafe
expect_exit 0 "--validate (cbom)"                -- poam generate --from cbom "$EX/example.cbom.json" --validate
expect_exit 0 "qureddy + ext + validate"         -- poam generate --from qureddy "$EX/example.scan.json" --extension breachsafe --validate
expect_exit 0 "--to json explicit"               -- poam generate --from cbom "$EX/example.cbom.json" --to json
expect_exit 0 "--extension repeated (idempotent)" -- poam generate --from cbom "$EX/example.cbom.json" --extension breachsafe --extension breachsafe
# stdin (the flagship pipe)
if cat "$EX/example.cbom.json" | $MINT poam generate --from cbom - >/dev/null 2>&1; then _ok "stdin '-' pipe (exit 0)"; else _no "stdin '-' pipe"; fi

echo "-- logging flags (STDERR only; STDOUT stays pure OSCAL) --"
CB=(poam generate --from cbom "$EX/example.cbom.json")
stderr_lacks "minted_document" "default level is quiet on success (no INFO)" -- "${CB[@]}"
stderr_has "minted_document" "-v surfaces the INFO run summary"      -- "${CB[@]}" -v
expect_exit 0 "-vv (DEBUG) exits 0"                                  -- "${CB[@]}" -vv
stdout_valid_json "-vv keeps STDOUT a pure OSCAL channel"            -- "${CB[@]}" -vv
stderr_lacks "semantic_checks_passed" "-q suppresses the --validate WARNING" -- "${CB[@]}" --validate -q
stderr_ndjson "--json-logs emits NDJSON on STDERR"                   -- "${CB[@]}" -v --json-logs

echo "-- standalone validator: poam validate <file> (no oscal-cli/trestle) --"
$MINT poam generate --from cbom "$EX/example.cbom.json" 2>/dev/null >"$TMP/good.poam.json"
expect_exit 0 "validate a valid POA&M"           -- poam validate "$TMP/good.poam.json"
expect_exit 1 "validate a broken POA&M -> exit 1" -- poam validate "$EX/broken.poam.json"
stderr_has "semantic_error" "broken POA&M reports the problem" -- poam validate "$EX/broken.poam.json"
# #73: empty poam-items (schema minItems 1) is caught by the cardinality validator.
"$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));d["plan-of-action-and-milestones"]["poam-items"]=[];json.dump(d,open(sys.argv[2],"w"))' "$TMP/good.poam.json" "$TMP/empty-items.poam.json"
expect_exit 1 "validate empty poam-items -> exit 1 (minItems)" -- poam validate "$TMP/empty-items.poam.json"
# #72: a non-POA&M document is an INPUT error (2), not a validation failure (1).
expect_exit 2 "validate a non-POA&M doc -> exit 2 (input)" -- poam validate "$TMP/bad.cbom.json"
expect_exit 2 "validate a missing file -> exit 2" -- poam validate "$TMP/does-not-exist.json"
expect_exit 4 "validate with no document arg -> usage 4" -- poam validate
# #74: an import-ssp POA&M whose observation subjects are type=component and whose related-risk
# resolves in the imported SSP (not the local `risks`) must NOT false-red — mint cannot follow
# `import-ssp`, so it must not assert those cross-refs are dangling (matches trestle/oscal-cli).
"$PY" -c '
import json, sys
d = json.load(open(sys.argv[1])); p = d["plan-of-action-and-milestones"]
p["import-ssp"] = {"href": "ssp.json"}
for o in p.get("observations", []):
    for s in o.get("subjects", []): s["type"] = "component"
p["poam-items"][0].setdefault("related-risks", []).append({"risk-uuid": "401c15c9-ad6b-4d4a-a591-7d53a3abb3b6"})
json.dump(d, open(sys.argv[2], "w"))' "$TMP/good.poam.json" "$TMP/import-ssp.poam.json"
expect_exit 0 "#74 import-ssp: component subject + external risk-uuid not false-red" -- poam validate "$TMP/import-ssp.poam.json"
# #74 controls: WITHOUT import-ssp the same dangling refs ARE still caught (self-contained POA&M).
"$PY" -c '
import json, sys
d = json.load(open(sys.argv[1])); p = d["plan-of-action-and-milestones"]
p["poam-items"][0].setdefault("related-risks", []).append({"risk-uuid": "401c15c9-ad6b-4d4a-a591-7d53a3abb3b6"})
json.dump(d, open(sys.argv[2], "w"))' "$TMP/good.poam.json" "$TMP/dangling-risk.poam.json"
expect_exit 1 "#74 control: self-contained dangling risk-uuid still caught -> exit 1" -- poam validate "$TMP/dangling-risk.poam.json"
"$PY" -c '
import json, sys
d = json.load(open(sys.argv[1])); p = d["plan-of-action-and-milestones"]
p["observations"][0]["subjects"] = [{"type": "inventory-item", "subject-uuid": "deadbeef-dead-4ead-8ead-deaddeaddead"}]
json.dump(d, open(sys.argv[2], "w"))' "$TMP/good.poam.json" "$TMP/dangling-subject.poam.json"
expect_exit 1 "#74 control: self-contained dangling inventory-item subject still caught -> exit 1" -- poam validate "$TMP/dangling-subject.poam.json"
# the pipe: generate | validate -
if $MINT poam generate --from cbom "$EX/example.cbom.json" 2>/dev/null | $MINT poam validate - >/dev/null 2>&1
then _ok "generate | validate - (pipe, exit 0)"; else _no "generate | validate - pipe"; fi
expect_exit 0 "poam validate --help"             -- poam validate --help

echo "-- producer cross-check + evidence chain (--extension breachsafe on a qureddy CBOM) --"
QB=(poam generate --from cbom "$TMP/hybrid.qureddy.cbom.json")
stdout_has "producer-confirmed" "producer verdict matches derived -> producer-confirmed" -- "${QB[@]}" --extension breachsafe
stdout_has "relevant-evidence"  "evidence chain carried into the POA&M"                   -- "${QB[@]}" --extension breachsafe
stdout_has "stdout_sha256"      "evidence sha256 preserved in relevant-evidence"          -- "${QB[@]}" --extension breachsafe
# honest-failure: producer over-claims quantum_ready, mint derived transitional_hybrid
stdout_has "conflict:producer=quantum_ready,derived=transitional_hybrid" "conflict recorded, derived kept" -- poam generate --from cbom "$TMP/conflict.qureddy.cbom.json" --extension breachsafe
# neutral path: no --extension -> no provenance, no evidence, no qureddy leak
if "$MINT" "${QB[@]}" 2>/dev/null | grep -qF "provenance"; then _no "neutral --from cbom leaked provenance"; else _ok "neutral --from cbom stays vendor-neutral (no provenance/evidence)"; fi
# #76: a stray non-CBOM field in a qureddy scan must not crash the enricher (never-raises)
"$PY" -c 'import json,sys;d=json.load(open(sys.argv[1]));d["components"]=5;json.dump(d,open(sys.argv[2],"w"))' "$EX/example.scan.json" "$TMP/stray.scan.json"
expect_exit 0 "enricher ignores a stray non-CBOM field (never-raises, #76)" -- poam generate --from qureddy "$TMP/stray.scan.json" --extension breachsafe

echo "-- usage errors (exit 4, distinct from bad input) --"
expect_exit 4 "invalid --from choice"            -- poam generate --from nope "$EX/example.cbom.json"
expect_exit 4 "missing required report arg"      -- poam generate --from cbom
expect_exit 4 "invalid --to choice"              -- poam generate --from cbom "$EX/example.cbom.json" --to bogus
expect_exit 4 "invalid --extension choice"       -- poam generate --from cbom "$EX/example.cbom.json" --extension nope

echo "-- input / dependency errors (clean exit, no traceback) --"
expect_exit 2 "missing file"                     -- poam generate --from cbom "$TMP/does-not-exist.json"
expect_exit 2 "invalid JSON"                     -- poam generate --from cbom "$TMP/notjson.json"
expect_exit 2 "malformed CBOM (bomFormat)"       -- poam generate --from cbom "$TMP/bad.cbom.json"
expect_exit 2 "malformed qureddy (no target)"    -- poam generate --from qureddy "$TMP/bad.scan.json"
expect_exit 3 "--to xml without oscal-cli"       -- poam generate --from cbom "$EX/example.cbom.json" --to xml
expect_exit 3 "--to yaml without oscal-cli"      -- poam generate --from cbom "$EX/example.cbom.json" --to yaml
expect_exit 3 "stub model 'ar' -> not-implemented" -- ar generate --from cbom "$EX/example.cbom.json"

echo "-- honest-failure regression guards --"
readiness_is classically_weak true  "#67 legacy TLS 'TLSv1.0' string caps at classically_weak" "$TMP/tlsv10.cbom.json"
readiness_is transitional_hybrid false "#68 RSA key transport (pke) is scored (not quantum_ready)" "$TMP/rsa_pke.cbom.json"
readiness_is quantum_ready false "control: modern KEM-only is not over-flagged" "$TMP/allsafe.cbom.json"

echo "-- #64 zero-finding scan --"
expect_exit 0 "zero-finding scan mints a POA&M"  -- poam generate --from qureddy "$TMP/empty.scan.json"
stdout_has "No findings" "zero-finding -> honest 'No findings' item" -- poam generate --from qureddy "$TMP/empty.scan.json"
expect_exit 0 "zero-finding scan --validate clean" -- poam generate --from qureddy "$TMP/empty.scan.json" --validate

echo "-- determinism + never-raises --"
h1="$($MINT poam generate --from cbom "$EX/example.cbom.json" 2>/dev/null | shasum | cut -d' ' -f1)"
h2="$($MINT poam generate --from cbom "$EX/example.cbom.json" 2>/dev/null | shasum | cut -d' ' -f1)"
[ "$h1" = "$h2" ] && _ok "byte-deterministic across runs ($h1)" || _no "non-deterministic ($h1 != $h2)"
$MINT poam generate --from cbom "$TMP/bad.cbom.json" >/dev/null 2>"$TMP/e"
if grep -q "Traceback" "$TMP/e"; then _no "malformed input leaked a Python traceback"; else _ok "malformed input never leaks a traceback"; fi

echo "-- NIST oscal-cli Layer-1 conformance (optional) --"
if command -v oscal-cli >/dev/null 2>&1; then
  $MINT poam generate --from cbom "$EX/example.cbom.json" 2>/dev/null >"$TMP/poam.json"
  out="$(oscal-cli poam validate "$TMP/poam.json" 2>&1)"
  if echo "$out" | grep -q "is valid" && ! echo "$out" | grep -q "is invalid"; then
    _ok "oscal-cli reports the minted POA&M valid"
  else _no "oscal-cli did NOT report the minted POA&M valid"; fi
else
  echo "  SKIP  oscal-cli not on PATH (install to enable authoritative Layer-1 gate)"
fi

echo "======================================================================================"
printf "  %d passed, %d failed\n" "$pass" "$fail"
[ "$fail" -eq 0 ] && { echo "  OK"; exit 0; } || { echo "  FAILURES"; exit "$fail"; }
