# Smart Tools

A smart tool is a self-contained tool that ships with its own AI capability built in.
It behaves like an ordinary library or CLI, and its straight code paths run with no model provider
configured. Alongside those, it exposes higher-level commands that invoke AI capabilities
under the hood, so a caller states what it wants rather than loading a domain's worth of
context and doing the work itself.

## Overview

Hard-won domain expertise tends to stay where it was built. How to stand up an isolated
environment that actually mirrors production. How to get a useful answer out of Microsoft 365. 
How to turn a pile of material into a beautifully designed presentation. 
Each of these is real knowledge, and each is usually only consumable from 
inside the harness it was built for, with the right skills and context loaded.

A smart tool packages one domain's expertise so it can be consumed anywhere: Copilot,
Claude Code, a Python service, a shell script, or any future agent.
The tool holds the domain knowledge, the workflows, and the choice of which of its own
capabilities to use. The caller states an intent and gets a result, usually a structured
artifact it can hand straight to code.

This describes a shape for building smart tools, not a wire format for interoperating with
third-party runtimes. Anyone may follow it, but cross-vendor interoperation is not a goal it
serves.

## Design principles

Smart tools are built on three principles that inform everything else in this specification:

1. **A smart tool is standalone.** It is a library before it is anything else, which lets the
   same capability appear in a CLI, in a bespoke UI, embedded in someone's app, or driven by
   any agent.

2. **The AI is what makes it smart.** A smart tool has to do something genuinely powered by
   a model. If every path through it is deterministic code, it is a tool, and that is fine,
   but it is not a smart tool. The straight code paths still run with no provider
   configured, and a caller who never touches the smart commands never needs model
   credentials.

3. **The caller is usually an agent.** A failure names what went wrong and how to correct
   it, so the caller can act without a user going to read the documentation. A smart
   command invoked with no provider configured says exactly that and says what to
   configure, so the agent either fixes the problem or tells the user precisely how to. A
   tool that fails with an empty result or a bare stack trace has handed back a problem its
   caller cannot resolve.

## The specification

- **[Structure](structure.md)**: the layers a smart tool is built from. Library core, CLI
  wrapper, optional additional surfaces, and the rules governing the shipped AI capability.
- **[Manifest](manifest.md)**: how a smart tool describes itself: what it is, what it is
  for, and what it runs on. This is the artifact a registry will later consume, and it
  ships with the tool.
- **[Invocation](invocation.md)**: calling a smart tool. Straight and smart paths,
  self-description, passing context in, getting artifacts out, and failure semantics.

[Examples](examples.md) lists example smart tools.

Future parts and ideas of the spec are documented in [`ROADMAP.md`](../ROADMAP.md).
