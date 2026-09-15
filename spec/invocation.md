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
types, and what each returns. Self-description covers how to drive the tool. The manifest's
frontmatter covers whether to reach for it at all, and is reachable from the library in the
same way.

Most of this is native to a library. Signatures and docstrings carry the names, arguments,
types, and return shapes, and a caller holding the library reads them the way it reads any
other dependency. Based on the documentation and help text of the library and other surfaces,
it should be clear which functionality is AI-enabled. If it is genuinely ambiguous, it can
be explicitly stated which capabilities require AI.

The CLI renders what the library exposes, at two levels of detail for two different readers.

`-h` is the user summary. Terse and scannable: the capabilities and a line about each. It is
what someone types when they want to remember the name of a flag.

`--help` is the skill: what an agent reads once it has decided to use the tool. It has the
shape of an [Agent Skill](https://agentskills.io/specification) as a host delivers one to a
model.

```
<skill_content name="doc-summarizer">
Skill directory: /home/user/.venv/lib/python3.13/site-packages/doc_summarizer
Repository: https://github.com/example/doc-summarizer
Relative paths in this skill are relative to the skill directory.

# doc-summarizer

Condenses long documents into summaries a reader can act on.

**The library is the tool.** `doc_summarizer.lib` holds every capability. ...

## When to reach for it

...

## Capabilities

- `manifest` [deterministic] -- Print the tool's manifest as JSON. Arguments, result, and exit codes: `doc-summarizer manifest --help`.
- `summarize` [model-backed] -- Condense a document. Arguments, result, and exit codes: `doc-summarizer summarize --help`.

<skill_resources>
  <file>SMART_TOOL.md</file>
  <file>lib.py</file>
</skill_resources>
</skill_content>
```

**Skill directory** is the installed package root, resolved by the library at runtime. It
puts the tool's own files in reach: the manifest, the library source, anything shipped
alongside.

**Repository** is the tool's canonical source, read from the package metadata, for a caller
that can run the tool but cannot read its files. Omitted when the package declares none.

**The body** is the manifest body under a heading carrying the tool's name. Markdown, no
frontmatter, no usage line. It says what an agent would otherwise get wrong: when to reach
for the tool and when not, install and prerequisites, worked invocations, sharp edges, where
to read more. The Agent Skills ceiling of 500 lines applies. The manifest body is the
baseline; a tool may render more, or differently, when it knows something at runtime the
file cannot, such as whether a provider is configured.

**Capabilities** is generated from the tool's own surface: one line each, deterministic or
model-backed, each pointing at `<tool> <capability> --help`. That per-capability listing is
required for every capability and carries the arguments, return, and failures that do not
belong in the skill.

**Resources** lists the files the body refers to, relative to the skill directory. Every
path resolves after installation, so the files ship inside the package. Omitted when there
is nothing to list.

The library exposes the skill and each piece it is built from. The CLI prints it and adds
nothing.

### Shipping an Agent Skill alongside

A tool may also ship an Agent Skill, `skills/<name>/SKILL.md` in its repository. This is
optional. It exists for hosts that speak Agent Skills but know nothing about smart tools:
Claude Code, Copilot, or any harness that discovers `SKILL.md` files. Through it, such a
host learns the tool exists and how to start using it without anyone teaching it what a
smart tool is.

The skill carries the manifest's name and description, the install commands, and the
instruction to run `--help` and follow it. Nothing more. The tool brings the rest with it
through `--help`, so the skill stays correct when the tool changes and there is one place
the guidance is written.

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

The output format is part of each capability's documented interface, rather than a single
format prescribed by this specification. Results may be plain text, formatted text such as
Markdown, or structured data such as JSON. At the library level, these are ordinary return
values based on whatever is appropriate for that capability. Choose a format that suits the
result and how callers will use it.

A CLI can default to readable text and offer structured output through a flag such as
`--json` or `--output json`. Supporting both is useful when the same result serves readers
and downstream code, but is *not* required for each capability. Help text and documentation
should describe the default and any supported alternatives.

Stdout carries the requested result, whether text or structured data. Stderr carries
diagnostics such as progress messages and warnings, keeping them separate from results
that callers may pipe to another command or save to a file.

Where a capability writes an artifact, such as a profile, document, or configuration, to a
file, the result clearly identifies its location.

Capabilities, smart or not, and within one tool or across several, compose by writing a
script against the libraries, where results are typed return values rather than text to
parse. The help text says so, so a caller chaining capabilities reaches for the library
instead of piping CLI output.

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
