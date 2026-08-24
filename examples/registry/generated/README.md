<!-- SPDX-FileCopyrightText: 2026 BreachSAFE -->
<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# Generated OSCAL artifacts

## Contents

1. [Purpose](#purpose)
2. [Rules](#rules)

## Purpose

This directory is reserved for OSCAL Catalog, Profile, and Assessment artifacts generated
from the editable registry source. It is deliberately empty in the current release because
the Profile compiler is tracked separately in issues #153–#156.

## Rules

- Never edit generated files as a source of truth.
- Every generated artifact must be reproducible from `../registry.yaml` and its pinned Catalogs.
- A generator must record its tool and source revision in the release receipt before artifacts
  are published.
