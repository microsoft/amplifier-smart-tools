# Examples

Working smart tools that demonstrate the shape this specification describes. Each
lives in its own repository.

## Reference implementations

- **[amplifier-smart-tool-tmux](https://github.com/microsoft/amplifier-smart-tool-tmux)**
  at `main` — a smart tool for tmux fleets. A good example of the full shape: a
  library-first package with a thin CLI, a `SMART_TOOL.md` manifest, deterministic
  verbs that run with no provider configured (`sessions`, `read`, `doctor`,
  `exit-code`, …), and model-backed verbs (`triage`, `interpret`) that fail loud
  with a named remedy when no AI substrate is configured rather than silently
  degrading. It enforces this repository's [conformance kit](../conformance/README.md)
  in its own CI on every push.

<!-- To add a reference implementation:
     - **[name](repo-url)** at `ref` - what it is a good example of. -->
