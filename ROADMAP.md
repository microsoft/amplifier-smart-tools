# Roadmap

The specification says what is decided. This says what is not.

Each area below states a question the specification deliberately leaves open, why it is
open, and what would settle it. Areas are ordered by which is expected to force a decision
first, not by importance. This reflects current thinking rather than firm commitments. 

## Areas

### 1. Long-running and expensive calls

A capability that fans out across a domain can run far longer than a caller expects a
function call to take, and a model-backed one costs something every time it runs. The
specification addresses neither. There is no way for a capability to report progress, stream
intermediate output, or be cancelled, and no way for a result to carry what it cost in
tokens or time.

This is the gap a real tool is most likely to hit first. A caller that has waited ninety
seconds with no output cannot tell whether the tool is working or hung, and an agent
budgeting across many calls has nothing to budget with.

**What would settle it:** a tool with a genuinely slow capability. The shape of its progress
reporting is worth generalizing once one exists, and not before.

### 2. What a tool discloses about itself

The specification says callers are told which capabilities are model-backed, on the grounds
that cost and determinism are the caller's business. The library declares it and the CLI
renders it.

The competing position is that a tool should be implementation-invisible, so that it stays
free to change how a capability is implemented without breaking anyone. Both are defensible
and they conflict.

**What would settle it:** a decision rather than evidence. This one does not resolve by
building. Dropping the distinction would touch several sections of the invocation chapter
and the disclosure rule in the structure chapter, and nothing else.

### 3. Conventions shared across tools

Context granularity is described as none, partial, and full, but as useful granularity
rather than as a required parameter carrying those names. Whether it becomes a convention
every smart tool follows, or stays each tool's own choice, is undecided.

**What would settle it:** two tools built independently. If both reach for the same shape
without coordinating, it is a convention worth writing down. If they do not, it is not.

### 4. Packaging and distribution

How a smart tool is published and installed is unresolved.

Related to it: today each tool implements its own wrappers by following the same pattern.
The alternative is a generator that emits CLI and MCP surfaces from the library, or a
generic host that loads libraries and exposes them. Both have been raised, neither has been
tried, and the pattern is cheap enough to keep until one of them is.

**What would settle it:** the third or fourth tool. Two is not enough repetition to justify
a generator.

## Beyond the specification

These are not open questions within the specification. They are separate work with their own
shape, kept out so the specification stays about what a single tool is.

**Registry and discovery.** There will be a registry, and discovery is its own project. Its
format is undecided. The specification requires only that each tool own a self-description
at its own distribution root, so a registry can consume it whenever one exists.

**Host awareness.** The inverse direction, where a host automatically discovers and offers
the smart tools already installed, is secondary and not blocking. Tools ship first.
