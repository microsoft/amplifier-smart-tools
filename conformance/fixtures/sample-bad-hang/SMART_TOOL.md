---
smart_tool_format: 1
name: samplegood
version: 0.1.0
description: >
  A minimal reference smart tool used to exercise the conformance kit. It counts
  text deterministically and offers one model-backed summary capability. Use it
  when you need a known-good smart tool to validate tooling against.
use_cases:
  - Validate a smart-tools conformance kit against a passing tool
  - Demonstrate the deterministic versus model-backed split in one small package
platforms:
  - linux
  - macos
requires:
  - name: sample-provider
    purpose: Backs the 'summarize' capability. Without it, only the deterministic verbs run.
    optional: true
    install: README.md
---

# samplegood

A tiny reference smart tool. `stats` is deterministic and runs with no provider
configured. `summarize` is model-backed and fails loudly with a remedy when no
provider is present -- it never silently degrades.

This body is free-form guidance and carries no compatibility guarantee.
