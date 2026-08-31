# Roadmap

The specification says what is decided. This says what is not.

Each area below states a question the specification deliberately leaves open, why it is
open, and what would settle it. Areas are ordered by which is expected to force a decision
first, not by importance. This reflects current thinking rather than firm commitments. 

## Active Open Decisions

### 1. Long-running and expensive calls

Currently nothing prescribes or shows examples of how to handle long running calls.
For example, a smart tool capability might call an agent that runs for over an hour, but
to the caller, it *could* output nothing during that time and be valid. Should we consider
advocating in the spec to periodically return progress, or even suggest to output agent messages
as they come?

### 2. Details about how to integrate the intelligence into a smart tool

Currently the spec does not mention anything about what an AI integration looks like for the
smart capabilities. Right now we delegate this exclusively to the examples.

### 3. How other products consume smart tools

Nothing says what a product like the Amplifier App CLI, Copilot CLI, or Claude Code does to make
an installed smart tool available to its agent. Does every tool ship a skill, or
does one skill teach a host to find the installed tools and read their manifests?

### 4. Generated wrappers

Should we provide or suggest tools for generating wrappers for SDKs in other languages or MCP
servers?

## Beyond

**Registry and discovery.** There will be a registry, and discovery is its own project. Its
format is undecided. The specification requires only that each tool own a self-description
at its own distribution root, so a registry can consume it whenever one exists.

**Host awareness.** The inverse direction, where a host automatically discovers and offers
the smart tools already installed, is secondary and not blocking. Tools ship first.
