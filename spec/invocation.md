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
types, what each returns, and which of them are model-backed. Self-description covers how to
drive the tool. The manifest covers whether to reach for it at all, and is reachable from the
library in the same way.

Most of this is native to a library. Signatures and docstrings carry the names, arguments,
types, and return shapes, and a caller holding the library reads them the way it reads any
other dependency. Based on the documentation and help text of the library and other surfaces,
it should be clear which functionality is AI-enabled. If it is genuinely ambiguous, it can
be explicitly stated which capabilities require AI.

The CLI renders what the library exposes, at two levels of detail for two different readers.
Depending on the tool and structure of it, `-h` and `--help` are perfectly acceptable
to be equivalent.

`-h` is the user summary. Terse and scannable: the capabilities and a line about each. It is
what someone types when they want to remember the name of a flag.

`--help` is the complete listing, written for an agent deciding how to call the tool. Every
capability, its arguments and their types and what it returns. It is longer than a person wants
to read, and complete rather than selective. It is usually different from `-h` for tools who
have large surfaces.

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
selects and packages the context should be code the caller controls. The tool can decide
if its own intelligence takes advantage of the working directory with tools like read, bash,
etc. as another means of providing context. The tool's documentation should make it clear
how it works and how to configure permissions and scope of actions.

## What comes back

A result a caller can act on without parsing prose. At the library level, that means
ordinary return values. At the CLI, structured output on stdout is the encouraged default,
because a caller that can parse a result can chain it. Plain text is fine where the result
is genuinely a scalar or a single line and a format would be ceremony.

The test is whether the caller can hand the result to the next step without guessing. A
model-backed capability that returns a paragraph of explanation where a value was asked for
has moved the work of understanding back onto the caller.

Where a tool emits machine-readable output, stdout is the channel for it and stderr is the
channel for anything addressed to a human: progress, warnings, summaries. Splitting by
audience rather than by severity keeps a piped stdout parseable without suppressing what a
person watching the run needs to see.

Where a capability produces an artifact, a profile, a document, a configuration, the result
identifies the artifact rather than embedding it in a message.

## Where a tool puts its files

State, caches, logs, and temporary files belong outside the tool's own directory. A smart
tool is installed from a distribution it does not own and is invoked from a working
directory it did not choose, so neither is a safe place to write. State goes to the
conventional per-user location for the platform, temporary files to a temporary directory,
and output artifacts where the caller asked for them.

A tool that writes beside its own source is relying on having been run from a checkout. It
scatters files into the tree it was installed from, and those files reach a repository, a
pull request, or a published package without anyone deciding they should.

## Failure

Failures are loud and they name the remedy. A caller should never have to infer what went
wrong from an empty result.

At the CLI, a failure exits non-zero. This is the one part of a failure a caller can rely on
without parsing anything, and it is what every script, pipeline, and agent harness already
checks. A tool that describes an error in its output while exiting 0 has hidden that error
from all of them.

A tool also never waits on input a caller cannot supply. Invoked non-interactively, with
stdin closed, it completes or it fails, rather than blocking on a prompt that the agent on
the other end has no way to answer.

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
