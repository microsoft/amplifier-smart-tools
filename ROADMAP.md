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

Nothing says what a product like the Amplifier App CLI, Copilot CLI, or Claude Code should do to
make smart tools known to the host. For those wanting to integrate smart tools today, we
require that each smart tool provide a `smart-tool.json`, which points to the manifest. The
manifest can be used to determine how to advertise the tool to an agent. The descriptor also
names the argv prefix that starts the tool's CLI, plus a deterministic capability that runs
with no provider configured, so a platform can verify the install. A platform integrating
smart tools would need to supply the environment in which those tools run, including network
access and configured LLM providers.

### 4. AI Provider Interface

Every smart tool hinges on setup of an AI provider of some sort. What do we want to provide
to make this common or more streamlined? Currently we rely on the examples.

### 5. Continuing a smart call

A smart capability is a single shot today: arguments in, a result out. Sometimes a tool needs to
ask a clarifying question before it can do the work, or a caller wants to continue from the same
underlying session instead of starting over. Do we say anything here, or leave it to the tool
given that a calling agent will usually just make another call?

### 6. Generated wrappers

Should we provide or suggest tools for generating wrappers for SDKs in other languages or MCP
servers?

## Beyond

**Registry and discovery.** There will be a registry, and discovery is its own project. Its
format is undecided. The specification requires only that each tool own a self-description
at its own distribution root, so a registry can consume it whenever one exists.

**Host awareness.** The inverse direction, where a host automatically discovers and offers
the smart tools already installed, is secondary and not blocking. Tools ship first.
