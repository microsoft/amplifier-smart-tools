# Manifest

Every smart tool carries a manifest: a single file, shipped with the tool, that says what
the tool is, what it is for, and what it needs in order to run. It is how a caller decides
whether this is the right tool before invoking anything, and it is what a registry will
consume once one exists.

The manifest travels with the tool's own source. Prerequisites and platform support change
when the code changes, so they are updated in the same commit. A registry reads from the
tool rather than holding its own copy.

## Selection, not operation

The manifest answers "is this the tool for my job, and can I run it here?" It does not answer
"how do I call it." The practical test: a field belongs in the manifest if a caller needs it
*before* deciding to install or invoke the tool. Everything else belongs in the tool.

## Where it lives

`SMART_TOOL.md`, in the tool's own source, beside the code that reads it. YAML frontmatter,
then a Markdown body.

The frontmatter is machine-readable and is the part other things depend on. The body is
free-form guidance for whoever is about to use the tool: when to reach for it, what it is
bad at, worked invocations.

The distribution root is the directory that produces the installable unit: the one holding
the package definition, such as `pyproject.toml` or `package.json`, and the descriptor
`smart-tool.json`. For a repository that ships a single smart tool, that is the repository
root.

There is one manifest and one copy of it. The library, the CLI, and every other adapter
answer "what is this tool, and can I run it here" from the same bytes, so they cannot
disagree about the tool's name, its version, or what it needs. It sits with the code because 
the source is what every surface is built from. A manifest there is reachable from all of 
them with nothing copied, generated, or kept in step.

Exactly where it sits is the tool's choice, because ecosystems differ in what a build can
carry into a published artifact and no one path suits them all. The descriptor at the
distribution root names it, so a reader opens one file at a known path and is told where
to look next.

```
my-smart-tool/
  smart-tool.json
  pyproject.toml
  src/
    my_smart_tool/
      SMART_TOOL.md
      __init__.py
```

A repository may ship several smart tools, each rooted at its own distribution:

```
platform-monorepo/
  README.md
  tools/
    doc-summarizer/
      smart-tool.json
      pyproject.toml
      src/doc_summarizer/SMART_TOOL.md
    log-triage/
      smart-tool.json
      package.json
      src/SMART_TOOL.md
```

The distributions in one repository need not share an ecosystem.

Exactly one manifest per distribution. A second `SMART_TOOL.md` under a distribution root
is *incorrect* and not a valid smart tool. A manifest under a nested descriptor belongs 
to that tool and does not count against this one.

## Reading it after installation

The manifest is included in whatever the tool publishes, and the library exposes it as
structured data read from the copy built into the tool. Callers reach the manifest through the library 
rather than by locating a file. Install layouts differ by ecosystem and no filesystem path is portable across them.

A file in the source tree and an accessor on the library are the same manifest reached
two ways. The file serves anything reading source: a registry scraping a repository, CI, a
person browsing. The library serves everything after installation. Wrappers expose the
accessor in whatever form suits them, and add nothing of their own.

## The frontmatter

Fields not listed here are not part of the manifest.

```yaml
smart_tool_format: 1
name: digital-twin-universe
version: 0.4.0
description: >
  Stands up isolated, realistic environments from a declarative profile so software
  can be tested as though actually deployed. Use when "tests pass locally" is not
  enough evidence.
use_cases:
  - Test a web app in a container that mirrors its real deployment
  - Simulate an end-user environment without touching production
  - Verify a CLI tool installs and runs cleanly from scratch
platforms:
  - linux
  - macos
requires:
  - name: incus
    purpose: Runs the isolated environments.
    install: docs/installing-incus.md
  - name: docker
    purpose: Mock service sidecars. Without it, profiles declaring sidecars cannot launch.
    optional: true
    install: docs/installing-docker.md
```

**`smart_tool_format`** is the manifest schema version, not the tool's version. It exists so
a reader can tell whether it understands the file at all.

**`name`** is lowercase alphanumeric and hyphens. It is the tool's identity across the
registry, the package index, and the CLI.

**`version`** is the tool's version, and it matches the version in the package definition.
A tool that publishes different versions in its package metadata, its manifest, and its docs
has three answers to a question that has one, and every consumer picks the wrong one
eventually.

**`description`** says what the tool does and when to reach for it, in that order. It is
read by users scanning a registry and by agents deciding whether to route work here, so it
should carry the words someone would actually use when they need this tool.

**`use_cases`** are the concrete jobs the tool is for. These are selection aids, not a
capability list, and they should read like things a person wants, not like functions the
tool exposes.

**`platforms`** is the set of operating systems the tool actually works on. Not the ones it
theoretically compiles for. A tool that has never been run on Windows does not list Windows.

**`requires`** declares what must exist in the environment before the tool can run. Each
entry carries `name`, `purpose`, and `install`, and may carry `optional`. `install` is a
reference to documentation, a relative path or a URL, never a command. `optional: true`
means the tool runs without the dependency in a reduced form, and that entry's `purpose`
states what is lost.

Every field in the manifest is inert. Nothing in it is a command, and reading a manifest
never runs anything. Detecting whether a prerequisite is present is the tool's own job.

Language runtimes and package dependencies are not listed here. Those belong to the packaging
system, which already resolves them.

## The body

Everything below the frontmatter is guidance, written for whoever is about to use the tool,
user or agent. Typical contents: when this tool is the right choice and when it is not,
sharp edges, worked invocations, and pointers to deeper documentation.

It carries no compatibility guarantee, and nothing may depend on a particular sentence
being present.
