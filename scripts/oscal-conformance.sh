#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# NIST OSCAL conformance gate (#71 / #17).
#
# mint-oscal claims to emit *NIST* OSCAL. Its own `poam validate` / `--validate` are
# in-process Layer-2 checks: "necessary but not sufficient" and NOT authoritative NIST
# schema/constraint validation. This gate closes that trust gap by validating minted
# output against the upstream reference validator, oscal-cli, exactly as an auditor would.
#
# What it does, end to end:
#   1. Mint a POA&M from a fixture CBOM via the real mint-oscal CLI.
#   2. Obtain oscal-cli 3.2.0 (detect a local install, else download from Maven Central).
#   3. POSITIVE control: the minted POA&M MUST be reported valid  -> else exit non-zero.
#   4. NEGATIVE control: the same doc with one required field removed MUST be rejected
#      -> if the validator rubber-stamps it, the gate is broken and we exit non-zero.
#
# Exit 0 iff both controls hold. Any other outcome is non-zero.
#
# ---------------------------------------------------------------------------------------
# oscal-cli provenance (single source of truth; keep the workflow + docs in sync):
#   Maven coordinate : dev.metaschema.oscal:oscal-cli-enhanced:3.2.0  (classifier oscal-cli, .zip)
#   Distribution zip : https://repo1.maven.org/maven2/dev/metaschema/oscal/oscal-cli-enhanced/3.2.0/oscal-cli-enhanced-3.2.0-oscal-cli.zip
#   Runtime          : a Java 17+ JRE (the CLI is pure Java; no native build needed)
# ---------------------------------------------------------------------------------------
#
# Usage:
#   scripts/oscal-conformance.sh                 # uses examples/example.cbom.json
#   scripts/oscal-conformance.sh path/to.cbom.json
#
# Overrides (all optional; the script auto-detects sensible defaults):
#   MINT="/path/to/mint-oscal"     CLI under test (else installed mint-oscal, else python -m)
#   PYTHON="/path/to/python"       interpreter for the python -m fallback + JSON mutation
#   JAVA_HOME="/path/to/jre17"     Java 17+ home (else $JAVA_HOME, then PATH `java`)
#   OSCAL_CLI="/path/to/oscal-cli" exact launcher (skips detection/download)
#   OSCAL_CLI_HOME="$HOME/.cache/mint-oscal"   download/cache dir for auto-fetched oscal-cli

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

OSCAL_CLI_VERSION="3.2.0"
OSCAL_CLI_ZIP_URL="https://repo1.maven.org/maven2/dev/metaschema/oscal/oscal-cli-enhanced/${OSCAL_CLI_VERSION}/oscal-cli-enhanced-${OSCAL_CLI_VERSION}-oscal-cli.zip"
CACHE_DIR="${OSCAL_CLI_HOME:-$HOME/.cache/mint-oscal}"

RED='\033[31m'; GREEN='\033[32m'; DIM='\033[2m'; BOLD='\033[1m'; NC='\033[0m'
info()  { printf "${DIM}%s${NC}\n" "$*"; }
ok()    { printf "  ${GREEN}PASS${NC}  %s\n" "$*"; }
bad()   { printf "  ${RED}FAIL${NC}  %s\n" "$*"; }
die()   { printf "${RED}${BOLD}conformance gate ERROR:${NC} %s\n" "$*" >&2; exit 2; }

# --- resolve a Python 3.12+ interpreter (mint-oscal's floor; 3.9 is BANNED) -----------
# Ambient `python3` is often an old system build (3.9 on macOS) that fails opaquely, so
# prefer $PYTHON, then a versioned python3.1x, and HARD-REQUIRE >= 3.12 (fail closed).
_py312() { command -v "$1" >/dev/null 2>&1 && "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 12) else 1)' 2>/dev/null; }
if [ -n "${PYTHON:-}" ]; then
  _py312 "$PYTHON" || die "PYTHON=$PYTHON is not Python 3.12+ (mint-oscal floor; 3.9 is banned)"
  PY="$PYTHON"
else
  PY=""
  for cand in python3.14 python3.13 python3.12 python3; do
    if _py312 "$cand"; then PY="$(command -v "$cand")"; break; fi
  done
  [ -n "$PY" ] || die "Python 3.12+ not found (3.9 is banned); install it or set PYTHON=/path/to/python3.12+"
fi

# --- resolve the mint-oscal CLI under test --------------------------------------------
if [ -n "${MINT:-}" ]; then
  :
elif command -v mint-oscal >/dev/null 2>&1; then
  MINT="mint-oscal"
else
  MINT="$PY -m mint_oscal.cli"
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi

# --- resolve a Java 17+ runtime -------------------------------------------------------
# Returns the major version of a `java` launcher (handles both "1.8.x" and "17.x").
_java_major() {
  local ver
  ver="$("$1" -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+)(\.([0-9]+))?.*/\1 \3/')" || return 1
  set -- $ver
  if [ "$1" = "1" ]; then echo "${2:-0}"; else echo "$1"; fi
}

# Sets globals JAVA_BIN and (when a home is known) exports JAVA_HOME. Not run in a
# subshell, so the JAVA_HOME export survives — oscal-cli's launcher reads it at runtime.
resolve_java() {
  local candidates=() home java major
  [ -n "${JAVA_HOME:-}" ] && candidates+=("$JAVA_HOME")
  # Common local locations (the proven BQP toolbox + a Homebrew Temurin).
  candidates+=(/tmp/oscal-tools/jdk-*/Contents/Home /opt/homebrew/opt/openjdk@17)
  for home in "${candidates[@]}"; do
    java="$home/bin/java"
    [ -x "$java" ] || continue
    major="$(_java_major "$java" 2>/dev/null)" || continue
    if [ "${major:-0}" -ge 17 ] 2>/dev/null; then
      export JAVA_HOME="$home"; JAVA_BIN="$java"; return 0
    fi
  done
  # Fall back to a PATH `java`; derive a JAVA_HOME from it when the layout allows.
  if command -v java >/dev/null 2>&1; then
    java="$(command -v java)"
    major="$(_java_major "$java" 2>/dev/null || echo 0)"
    if [ "${major:-0}" -ge 17 ] 2>/dev/null; then
      home="$(cd "$(dirname "$java")/.." 2>/dev/null && pwd || true)"
      [ -n "$home" ] && [ -x "$home/bin/java" ] && export JAVA_HOME="$home"
      JAVA_BIN="$java"; return 0
    fi
    die "found java (major ${major}) but oscal-cli needs Java 17+. Set JAVA_HOME to a 17+ JRE."
  fi
  die "no Java 17+ runtime found. oscal-cli is pure Java and needs a JRE 17+.
      Install one (macOS: brew install openjdk@17; Ubuntu: apt-get install openjdk-17-jre-headless)
      or set JAVA_HOME to an existing 17+ home."
}

# --- resolve (or download) oscal-cli --------------------------------------------------
resolve_oscal_cli() {
  # 1. explicit launcher
  if [ -n "${OSCAL_CLI:-}" ] && [ -x "$OSCAL_CLI" ]; then echo "$OSCAL_CLI"; return 0; fi
  # 2. on PATH
  if command -v oscal-cli >/dev/null 2>&1; then command -v oscal-cli; return 0; fi
  # 3. proven local toolbox
  if [ -x /tmp/oscal-tools/oscal-cli-dist/bin/oscal-cli ]; then
    echo /tmp/oscal-tools/oscal-cli-dist/bin/oscal-cli; return 0
  fi
  # 4. cache from a prior run
  local cached
  cached="$(ls "$CACHE_DIR"/oscal-cli-*/bin/oscal-cli 2>/dev/null | head -1 || true)"
  if [ -n "$cached" ] && [ -x "$cached" ]; then echo "$cached"; return 0; fi
  # 5. download from Maven Central
  info "oscal-cli not found; downloading ${OSCAL_CLI_VERSION} from Maven Central..." >&2
  command -v curl  >/dev/null 2>&1 || die "curl is required to download oscal-cli"
  command -v unzip >/dev/null 2>&1 || die "unzip is required to unpack oscal-cli"
  mkdir -p "$CACHE_DIR"
  local dest="$CACHE_DIR/oscal-cli-${OSCAL_CLI_VERSION}"
  curl -sSfL "$OSCAL_CLI_ZIP_URL" -o "$TMP/oscal-cli.zip" \
    || die "download failed: $OSCAL_CLI_ZIP_URL"
  rm -rf "$dest"; mkdir -p "$dest"
  # The zip may or may not carry a top-level dir; flatten so bin/ lands at $dest/bin.
  unzip -q "$TMP/oscal-cli.zip" -d "$TMP/unz" || die "unzip failed"
  local binpath
  binpath="$(find "$TMP/unz" -type f -name oscal-cli -path '*/bin/*' | head -1)"
  [ -n "$binpath" ] || die "downloaded archive has no bin/oscal-cli"
  cp -R "$(dirname "$(dirname "$binpath")")"/. "$dest"/
  chmod +x "$dest/bin/oscal-cli"
  echo "$dest/bin/oscal-cli"
}

# --- run oscal-cli and judge the verdict ----------------------------------------------
# oscal-cli prints "... is valid." on success and "... is invalid." on failure. We assert
# on BOTH the exit code and the verdict string: "is valid" is not a substring of
# "is invalid", so the two are unambiguous even if a future build's exit code drifts.
#   valid()   -> 0 only when reported valid AND exit 0
#   invalid() -> 0 only when reported invalid (or non-zero exit) -- i.e. correctly rejected
validate_verdict() {  # <oscal-cli> <file> -> echoes "VALID"|"INVALID", sets no exit
  local cli="$1" file="$2" out rc
  out="$("$cli" validate "$file" 2>&1)"; rc=$?
  if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "is valid"; then
    echo "VALID"
  else
    echo "INVALID"
  fi
}

# ======================================================================================
CBOM="${1:-$ROOT/examples/example.cbom.json}"
[ -f "$CBOM" ] || die "fixture CBOM not found: $CBOM"

printf "${BOLD}NIST OSCAL conformance gate${NC}  (oscal-cli %s, Maven Central)\n" "$OSCAL_CLI_VERSION"
JAVA_BIN=""
resolve_java
info "  java      : $JAVA_BIN  (JAVA_HOME=${JAVA_HOME:-<unset, using PATH>})"
CLI="$(resolve_oscal_cli)" || exit 2
info "  oscal-cli : $CLI"
info "  fixture   : $CBOM"
echo

fail=0

# 1. mint a POA&M from the fixture CBOM ------------------------------------------------
POAM="$TMP/minted.poam.json"
if $MINT poam generate --from cbom "$CBOM" >"$POAM" 2>"$TMP/mint.err"; then
  ok "minted POA&M from fixture CBOM"
else
  bad "mint-oscal failed to generate a POA&M"; sed 's/^/        /' "$TMP/mint.err" | head -5
  echo; printf "${RED}${BOLD}CONFORMANCE GATE FAILED${NC}\n"; exit 1
fi

# 2. POSITIVE control: minted POA&M must be NIST-valid ---------------------------------
if [ "$(validate_verdict "$CLI" "$POAM")" = "VALID" ]; then
  ok "oscal-cli reports the minted POA&M as VALID (positive control)"
else
  bad "oscal-cli rejected the minted POA&M — mint-oscal is emitting non-conformant OSCAL"
  "$CLI" validate "$POAM" 2>&1 | sed 's/^/        /' | tail -12
  fail=$((fail + 1))
fi

# 3. NEGATIVE control: mutate the valid doc (drop the required top-level uuid) ----------
# Proves the gate actually catches invalidity rather than rubber-stamping every input.
BROKEN="$TMP/broken.poam.json"
"$PY" - "$POAM" "$BROKEN" <<'PYEOF'
import json, sys
doc = json.load(open(sys.argv[1]))
doc["plan-of-action-and-milestones"].pop("uuid", None)  # uuid is REQUIRED by OSCAL
json.dump(doc, open(sys.argv[2], "w"))
PYEOF
if [ "$(validate_verdict "$CLI" "$BROKEN")" = "INVALID" ]; then
  ok "oscal-cli rejects a POA&M with the required uuid removed (negative control)"
else
  bad "oscal-cli ACCEPTED a known-invalid POA&M — the conformance gate is not working"
  fail=$((fail + 1))
fi

echo
if [ "$fail" -eq 0 ]; then
  printf "${GREEN}${BOLD}CONFORMANCE GATE PASSED${NC}  — minted OSCAL is valid per the NIST reference validator.\n"
  exit 0
else
  printf "${RED}${BOLD}CONFORMANCE GATE FAILED${NC}  (%d control(s) failed)\n" "$fail"
  exit 1
fi
