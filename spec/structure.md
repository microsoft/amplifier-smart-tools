# Structure

A smart tool is a library with wrappers around it. The library holds the capability; every
other surface is a thin adapter that exposes the same capability in a different shape.

This is the single decision that makes the rest possible. A capability that lives in a
library can be called from a CLI, an MCP server, a web service, someone's own app, or any
agent. A capability that lives in a CLI can only be called by whoever is willing to shell
out to it.

## The library is the tool

Everything the tool can do is reachable from the library.

The rule is one-directional and absolute: no capability exists only in a wrapper. If the
CLI can do it, the library can do it. If a wrapper needs behavior the library does not
have, that behavior gets added to the library and the wrapper calls it.

Wrappers may legitimately hold things that are genuinely about their own medium: argument
parsing, terminal output formatting, reading a file path into the string the library wants,
HTTP routing. None of that is capability. The test is whether removing the wrapper would
lose anything a different caller might want.

Callers who want to constrain the surface they depend on should put their own adapter in
front of the library, so their contract is with the adapter rather than with everything the
library happens to expose.

## The CLI

Every smart tool ships a CLI, and it is a thin wrapper.

It ships by default rather than on request. The CLI makes the tool usable from a shell
script, from an agent that can run commands, and from any harness that has no way to import
a library object, and it requires no integration work from the caller.

Thin means the CLI hooks up argument parsing and I/O conventions and then calls the
library. Domain logic in the CLI is a defect: it is capability the library cannot reach.

The CLI may add things that only make sense at a command line. Loading a file path into a
value the library takes as data is the common case, permitted while the library still
accepts the data directly.

## Optional surfaces

Anything beyond the library and the CLI is optional, and optional means the tool works
completely without it.

**MCP.** A smart tool may expose an MCP server. This is cheap to add once the library
boundary is clean and it makes the tool reachable from hosts that speak MCP and nothing
else. It is not required, and nothing in this specification assumes it exists.

**A web service or UI.** A tool may ship a local service and a browser interface, and for
some tools this is genuinely the right way to drive them. It must never be the only way,
and it must not start unless asked. A tool that spins up a web server as a side effect of
being used is doing something the caller did not request.

**Others.** Each new surface is a new adapter over the same library, and it adds no capability of its own.

## The AI capability

A smart tool has to do something genuinely powered by a model. If every path through it is
deterministic code, it is a tool, and that is fine, but it is not a smart tool.

At the same time, the straight code paths run with no model provider configured. A caller
that only wants the deterministic capabilities never has to supply model credentials, and
the tool must not refuse to load without them. A tool that demands a provider at import
time has made its AI capability mandatory, which is the opposite of what this asks for.

The model-backed paths are ordinary capabilities of the library. They take arguments, they
return values, and they live alongside the deterministic ones.

A caller is told which capabilities are model-backed, because cost and determinism are its
concern. How a capability is implemented beyond that is the tool's business: which model,
how many calls, what mix of code and inference.
