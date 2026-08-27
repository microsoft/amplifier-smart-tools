# Invocation

Calling a smart tool is like calling any other library or tool. Arguments in, a result out,
an error that says what went wrong. The fact that some paths consult a model is an
implementation detail of those paths, not a different calling convention.

This chapter covers what a caller passes in, what comes back, and what happens when things
fail.

## Straight and smart paths

A smart tool exposes both kinds of capability through one surface. There is no separate
mode to enter and no separate binary for the model-backed parts.

The difference that matters to a caller is not how a capability is implemented but what it
costs and how reliable it is. A deterministic path returns the same answer every time and
costs nothing beyond compute. A model-backed path may return a different answer on a second
run and consumes tokens. Callers making budget or retry decisions need to know which they
are invoking.

Callers who never invoke a model-backed path never need model credentials, and the tool
must not require them in order to load.

Beyond that signal, the internals stay the tool's business. A caller should not have to
know whether a given result came from code, from a model, or from both in order to use it
correctly.

## Self-description

A smart tool can describe its own surface: the capabilities it offers, their arguments and
types, what each returns, and which of them are model-backed.

Most of this is native to a library. Signatures and docstrings carry the names, arguments,
types, and return shapes, and a caller holding the library reads them the way it reads any
other dependency. Which capabilities are model-backed is not native to any language, and a
smart tool declares it in a form a caller can read programmatically.

The CLI renders what the library exposes, at two levels of detail for two different readers.

`-h` is the user summary. Terse and scannable: the capabilities and a line about each. It is
what someone types when they want to remember the name of a flag.

`--help` is the complete listing, written for an agent deciding how to call the tool. Every
capability, its arguments and their types, what it returns, and which capabilities are
model-backed. It is longer than a person wants to read, and complete rather than selective.

The two are not aliases. Neither adds anything the library does not already expose.

Self-description covers how to drive the tool. The manifest covers whether to reach for it
at all, and is reachable from the library in the same way.

## Passing context in

Smart paths take normal typed arguments like any other function. Alongside those, they
accept an optional context payload: additional material the caller already has that would
help the tool do the job well.

Two rules govern it.

**The payload is data, not a reference.** At the library level, a caller passes the actual
content. This keeps the library free of assumptions about where the caller's material lives
and keeps it usable from processes that have no filesystem in common with the caller. A CLI
wrapper may accept a file path and read it into the payload, because that is a convenience
of the command line, not a change to what the library accepts.

**The caller decides how much, and code assembles it.** How much context to hand over is
the caller's judgment. Something like none, partial, and full is the useful granularity,
matching what agent delegation already offers.

Assembly should be mechanical. When an agent composes the payload by deciding what seems
relevant, the tool's result becomes a function of that agent's summarizing rather than of
the material itself, and two callers with identical inputs get different answers. Whatever
selects and packages the context should be code the caller controls.

## What comes back

A result a caller can act on without parsing prose.

At the library level, that means ordinary return values: objects, dataclasses, dictionaries.
At the CLI, it means structured output on stdout. The test is whether the caller can hand
the result to the next step programmatically. A model-backed capability that returns a
paragraph of explanation has moved the work of understanding back onto the caller.

Where a capability produces an artifact, a profile, a document, a configuration, the result
identifies the artifact rather than embedding it in a message.

A capability that fans out across a domain can run far longer than a normal function call.
How progress is reported is not settled.

## Failure

Failures are loud and they name the remedy. A caller should never have to infer what went
wrong from an empty result.

Three cases are common enough to state:

**A missing prerequisite** fails immediately, naming what is absent and how to install it.
The manifest already declares these, so the failure and the manifest must agree.

**A smart path with no provider configured** fails saying exactly that, and says what to
configure. It does not fall back to a degraded deterministic answer, because a caller that
asked for the smart path and got a lesser result without being told has been misled about
what it received.

**A partial result** is a failure unless the capability documents partial completion as a
valid outcome, in which case the result says which parts succeeded. A capability never
silently returns the portion that worked.
