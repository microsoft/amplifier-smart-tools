# Amplifier Smart Tools

Smart Tools is a format for packaging domain expertise into tools that any agent can use.
Learn more and explore available tools on the [website](https://microsoft.github.io/amplifier-smart-tools/).

To get started install the [Smart Tools skill](skills/amplifier-smart-tools/SKILL.md) which helps your agent find, use, and create Smart Tools:

```bash
npx skills add microsoft/amplifier-smart-tools
```

## What are Smart Tools?

A smart tool is a self-contained tool that ships with its own AI capability built
in. It behaves like an ordinary library or CLI, and its straight code paths run
with no AI provider configured. Alongside those, it exposes higher-level
commands that invoke AI under the hood, so a caller states what it wants rather
than loading a domain's worth of context and doing the work itself.

At its core, a smart tool is a library, a manifest describing it, and a thin CLI
over the top. Anything else is an optional adapter over the same library.

```
my-smart-tool/
├── smart-tool.json         # Required: where the manifest is, how to launch the CLI
├── <package definition>    # Required: whatever the ecosystem uses
├── <library + thin CLI>    # Required: the library, plus a thin CLI over it
│   └── SMART_TOOL.md       # Required: the manifest, what it is and what it needs
└── ...                     # Optional: MCP server, web UI, other optional adapters
```

## Why Smart Tools?

Smart Tools bring their own "agent harnesses" inside which can be isolated without living inside another host and therefore behave the same whether called inside Copilot, Claude Code, a voice assistant using a fast model, etc.
This means that you get powerful capabilities out of the box that will work well wherever they are used, but also have lower level building blocks so they can be composed in new ways.
This approach has benefits when evaluating capabilities as author's evaluate the tool once, rather than within every host's differences. They can optimize for cost, quality, or local inference.

## How is this different from Skills, Agent Plugins, or MCP?

Agent Skills gave users a way to share prompts and scripts, and MCP gave users a way to connect agents to more things. 
Nothing gives users an easy way to use and share their tools and workflows in a way that is easily *composable* and easy to *evaluate* once in many different use cases and hosts.
When a smart tool is invoked by another agent, it is similar to delegating to a sub-agent: the domain expertise, context, and trajectory (message history) stay inside the tool, and the result is what comes back. 
A smart tool might even use skills, plugins, or MCP servers internally to implement its own capabilities. 
The caller does not have to be an agent as Skills and MCPs are usually used.
Every smart tool is a library underneath, so apps, scripts, and jobs can integrate one directly.
And not every capability is a smart one. A smart tool can also expose ordinary deterministic capabilities.

## What's in this repository

- **[spec/](spec/README.md)**: the specification, start here
  - **[Structure](spec/structure.md)**: the layers a smart tool is built from
  - **[Manifest](spec/manifest.md)**: how a smart tool describes itself
  - **[Invocation](spec/invocation.md)**: calling a smart tool
  - **[Packaging](spec/packaging.md)**: publishing, installing, and launching a smart tool
  - **[Examples](spec/examples.md)**: catalog of reference implementations
- **[conformance/](conformance/README.md)**: a machine-checkable kit for deciding whether something is a conforming smart tool
- **[skills/](skills/amplifier-smart-tools/SKILL.md)**: the agent skill that teaches an agent to find, install, invoke, create, and publish smart tools
- **[behaviors/](behaviors/smart-tools.yaml)**: the Amplifier behavior that composes that skill into an Amplifier session
- **[site/](site/README.md)**: the [website](https://microsoft.github.io/amplifier-smart-tools/) and the shared theme used across the Smart Tools family of sites
- **[docs/proposals/](docs/proposals/)**: discussion drafts for future parts of the spec; see [ROADMAP.md](ROADMAP.md) for what is still open

### Conformance

The [conformance kit](conformance/README.md) turns the specification's
must/must-not prose into executable checks. It is generic over any smart tool,
needs no install step, and is honest about what it cannot evaluate (a rule it
cannot check is reported `SKIP`, never a fabricated `PASS`). Run it against any
tool's distribution root:

```bash
uv run conformance/run.py path/to/your-smart-tool
```

### Installing in Amplifier

For the Amplifier App CLI, you can add the behavior instead; it composes the skill into every new Amplifier session:

```bash
amplifier bundle add 'git+https://github.com/microsoft/amplifier-smart-tools@main#subdirectory=behaviors/smart-tools.yaml' --app
```

Start a new session and use `/skills` to confirm the skill is listed. Update with
`amplifier update`, and stop composing it with:

```bash
amplifier bundle remove 'git+https://github.com/microsoft/amplifier-smart-tools@main#subdirectory=behaviors/smart-tools.yaml' --app
```

### Reference implementations

[spec/examples](spec/examples.md) lists reference smart tools.

### Roadmap

Check [ROADMAP.md](ROADMAP.md) for a sense of where the spec is going and things we are still thinking about.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.

## License

[MIT](LICENSE)
