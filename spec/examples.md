# Examples

Working smart tools that demonstrate the shape this specification describes. Each
lives in its own repository.

## Reference implementations

- **[amplifier-smart-tool-tmux](https://github.com/microsoft/amplifier-smart-tool-tmux)**
  A smart tool for managing tmux sessions across a machine. An example of the full smart tool shape:
  library-first package with a thin CLI, a `SMART_TOOL.md` manifest, deterministic
  verbs that run with no provider configured (`sessions`, `read`, `doctor`,
  `exit-code`, …), and model-backed verbs (`triage`, `interpret`).

- **[amplifier-smart-tool-digital-twin-universe](https://github.com/microsoft/amplifier-smart-tool-digital-twin-universe)**
  Stands up isolated VM or container environments from a declarative profile.
  An example of how to structure deterministic capabilities (in this case 
  launching environments from profiles or push/pull of files) and smart 
  capabilities (creating profiles from user requests or diagnosing issues).

<!-- To add a reference implementation:
     - **[name](repo-url)** at `ref` - what it is a good example of. -->
