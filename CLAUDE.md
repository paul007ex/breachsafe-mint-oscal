# BreachSAFE Mint-OSCAL contributor instructions

The executable agent card is [AGENTS.md](AGENTS.md). Read it after this repository policy and
before starting any non-trivial change; it points back to the full parent policy and applicable
skills.

## Contents

1. [Review and merge discipline](#review-and-merge-discipline)
2. [Verification](#verification)

## Review and merge discipline

Review pull requests one at a time against the current `main` branch. Do not stack PRs,
merge a dependent branch, or review an old branch against another feature branch. Before each
decision, refresh `main`, inspect the PR diff against `main`, and merge or reject that PR before
starting the next one. If a PR is stale or conflicts, update that PR branch or close it; do not
hide the conflict by stacking another PR on top.

## Verification

For each PR, record the exact PR number, base/head, mergeability, changed files, required checks,
and local quality-gate results. A green check run is evidence for that PR only; it does not
transfer to another PR. After merging, refresh `main` and verify the merged tree before reviewing
the next PR.
