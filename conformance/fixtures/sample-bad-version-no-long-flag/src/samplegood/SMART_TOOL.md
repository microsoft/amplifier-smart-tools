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
    install: docs/using-samplegood.md
---

## When to reach for it

- You need a known-good smart tool to point conformance tooling at.
- You want one small package that shows the deterministic / model-backed split.
- You are counting text and want an answer that is the same every time: `stats`
  needs no provider and costs nothing.

Not for real summarization work: `summarize` is a stub that truncates its input.

## Worked invocations

```bash
# Deterministic. Runs with no provider configured.
samplegood stats --text "hello world"

# Model-backed. Needs a provider credential in the environment.
SAMPLE_PROVIDER_KEY=... samplegood summarize --text "a longer passage to condense"
```

## Sharp edges

- `summarize` is model-backed. With no `SAMPLE_PROVIDER_KEY` set it exits 3 with
  a `no_provider` envelope naming the remedy; it never falls back to a
  deterministic answer.
- Every run, success or failure, writes exactly one JSON document to stdout.
  `docs/using-samplegood.md` gives the envelope shape and the exit codes.
