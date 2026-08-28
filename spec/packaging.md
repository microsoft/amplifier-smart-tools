# Packaging

How a smart tool is published, installed, and launched.

## Installation

Every smart tool installs from a git repository. That is the one method a tool must
support, and it is what lets a tool be used before it is published anywhere.

Publishing to an ecosystem registry is optional. An install script is permitted where
setup is more than placing a package: provisioning a runtime, compiling a native
component, installing system prerequisites. Such a script installs the tool and nothing
else.

## Ecosystem and runner

Two facts describe how a published tool is obtained and started:

```
ecosystem   where the package comes from      pypi, npm, cargo, oci, go, ...
runner      how it is started once obtained   uvx, npx, docker
```

Both are open vocabularies and the values above are examples. `runner` is absent where
the ecosystem installs a binary onto the path.

## The descriptor

`smart-tool.json`, at the distribution root. A directory holding one is a distribution
root.

Where the manifest sits and how the tool is started both follow from the ecosystem, so
neither can be derived by inspecting the distribution. The descriptor states them:

```json
{
  "manifest": "src/my_smart_tool/SMART_TOOL.md",
  "cli_argv": ["my-smart-tool"],
  "deterministic_smoke": ["manifest"]
}
```

```
manifest              required. Path to SMART_TOOL.md, relative to this file.
cli_argv              required. The argv prefix that starts the tool's CLI.
deterministic_smoke   a capability that runs with no provider configured.
```

Nothing about the tool itself appears here. Its name, version, and prerequisites live in
the manifest, so the two cannot disagree. `cli_argv` resolves to a build of the
distribution it sits in.

A descriptor bounds a distribution. Everything under the root belongs to that tool except
what falls under a nested descriptor, so a repository may vendor another tool's tree
without either becoming ambiguous.
