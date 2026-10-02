# Proposal: host channels and host-routed intelligence

**Discussion draft, 2026-10-02. Not an adopted specification or a change to Smart Tool v1 conformance.**

A Smart Tool installs from git and runs from a shell. Many of the hosts people now use do not
have a shell: desktop and web chat clients such as Claude Desktop, claude.ai and ChatGPT. They
do support **Agent Skills** and **MCP**, and several render **MCP Apps**. This proposal describes
how a tool can reach those hosts without changing what a Smart Tool is, and how a tool's model
steps can use the host's own model instead of a separately configured provider. It responds to
[ROADMAP](../../ROADMAP.md) items #3 (how products consume Smart Tools), #4 (AI provider
interface), #1 (long-running calls), #5 (continuing a call) and #6 (generated wrappers), and is a
companion to [collaborative surfaces](collaborative-surfaces.md), which covers retained work and
MCP App views.

The evidence comes from building and testing one tool across hosts
([Decisioncraft](https://github.com/michaeljabbour/amplifier-smart-tool-decisioncraft)); the
guarantees below are written to be tool-agnostic.

## What we observed

| Host | Shell | Skills | MCP | Behaviour when told "Install `<repo URL>`" |
| --- | --- | --- | --- | --- |
| Claude Code, Codex CLI, Amplifier | yes | yes | stdio | Installed from git, ran the deterministic smoke, used the tool |
| Claude Desktop | no | yes (ZIP upload; runs in a code sandbox) | stdio via MCP bundles (`.mcpb`); declares the MCP Apps UI extension; no sampling observed | Read the repository and wrote a review instead of installing |
| ChatGPT | no | yes (Skills) | remote HTTPS only (connectors); renders Apps SDK / MCP Apps views | Browsed the repository and asked what to do next |

Three consequences:

1. **"Install" means different things to different hosts.** Discovery guidance that assumes a
   shell leaves chat-only hosts with nothing to do except describe the tool.
2. **The skill is the one surface nearly every host shares.** Where a host runs skills in a code
   sandbox, a tool whose library has no runtime dependencies can ship *inside* the skill and run
   its deterministic capabilities there, with no installation, network or provider.
3. **Inside a host agent, the host's model is usually the right model.** A tool that reaches for
   an API key found in the environment can bill a person on a key they did not expect to use,
   while the agent they are working in sits idle. Desktop hosts may not offer MCP sampling, so
   "ask the host through sampling" is not a general answer either.

## Proposed guarantees

### 1. Channels are optional and additive

A tool may offer, in addition to the required git-installed CLI:

| Channel | What it is | Reaches |
| --- | --- | --- |
| `skill` | An Agent Skill folder (`SKILL.md` plus references) | Any skills host |
| `skill_portable` | The skill also vendors the dependency-free library and a small runner, so deterministic capabilities run in a sandbox with no network | Claude Desktop / claude.ai, ChatGPT Skills, other sandboxed hosts |
| `mcp` | An MCP adapter over the library (stdio argv; optionally a remote URL) | Coding agents, IDEs, desktop clients |
| `mcpb` | An MCP bundle release asset for one-click desktop install | Claude Desktop |
| `mcp_app` | An MCP App view for results (see collaborative surfaces) | Hosts that render MCP Apps |

Each channel is a thin adapter over the library; none adds a capability the library lacks. A
host or discovery agent picks the best channel it supports.

**Possible descriptor shape (for discussion only):** an optional `channels` object in
`smart-tool.json`, for example
`{"skill": "skills/<name>", "skill_portable": true, "mcp": {"argv": ["<tool>", "mcp"]}, "mcpb": "<tool>.mcpb"}`,
with release assets named stably so `releases/latest/download/<file>` resolves. The manifest stays
inert selection information; hosts must not execute anything from it.

### 2. Discovery guidance covers hosts without a shell

The discovery skill would gain a short decision tree:

1. Can you run a shell? Install from git and confirm with `deterministic_smoke`.
2. Do you support MCP bundles? Offer the bundle.
3. Do you run skills in a sandbox? Offer the portable skill ZIP and say where to add it.
4. Chat only, none of the above? Say so plainly and point to a host that can run the tool.

Never answer an install request with only a description of the tool.

### 3. Host-routed intelligence: the host can be the model

Roadmap #4 asks what a common provider interface should look like. Three patterns cover the
hosts we tested, in this order of preference **inside a host agent**:

1. **Starter pattern (host is the model).** The model-backed capability returns a structured
   task: the gathered material (with evidence references), the exact output schema, the writing
   rules, and the deterministic capability to call next (for example *validate* then *render*).
   The calling agent writes the output in its own turn; the tool validates it and refuses empty
   or placeholder results. This works in every host, with or without sampling or keys, and keeps
   the domain knowledge (schema, rules, validation) inside the tool.
2. **Sampling,** only when the client declares it and the user has allowed it.
3. **A configured provider** (API key, `--complete-cmd`-style command), only when the user chose
   it explicitly, or when the tool runs in a plain terminal with no host agent.

**Precedence rule:** inside a host agent, do not silently use an API key found in the
environment; use the host's model (starter or sampling) unless the person explicitly selected a
provider. Report which model will answer and who pays, for example in the tool's check verb.

This relaxes the current discovery guidance ("a model-backed capability with no provider
configured fails saying exactly that… do not silently do the work yourself") in one bounded way:
when the capability *returns a starter*, the host doing the work is the documented path, not a
silent substitution.

### 4. Long-running calls and continuation

- **Progress (roadmap #1):** human-readable progress on stderr, an optional event stream with
  `--json` (one JSON object per stage), and a time and cost estimate before expensive work.
- **Continuation (roadmap #5):** a caller-owned state folder (`--dir`), so a clarifying question
  and its answer are separate calls (`--next`, `--answer`) and nothing depends on a live session.

### 5. Generated wrappers (roadmap #6)

`smart-tool-creator` could generate the MCP adapter, the MCP bundle and the portable skill ZIP
from the manifest and capability list, so channels stay consistent with the library.

## Suggested optional conformance checks

Reported separately from v1 conformance:

- The skill's frontmatter parses under the Agent Skills format and stays within size guidance.
- The MCP adapter starts and lists its tools; tools, prompts and resources match any bundle
  manifest.
- The portable skill runs `deterministic_smoke` with no network and no installed packages.
- A built artifact (wheel, ZIP, bundle) contains every resource the library reads.
- **Trigger tests,** including false positives: prompts where a host should *not* invoke the tool
  (for example ordinary coding questions) and confirmation that it stays quiet.

## Open questions

- Whether `channels` belongs in `smart-tool.json` or in the catalog pointer.
- Naming for portable-skill runners and stable release-asset names.
- How hosts should surface "who pays" for model-backed capabilities.
- Whether remote MCP for chat clients without local MCP should be a recommended channel, and
  what authentication and filesystem limits it requires.
