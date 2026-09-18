# Proposal: optional collaborative surfaces for retained work

**Discussion draft, 2026-09-18. Not an adopted specification or a change to Smart Tool v1 conformance.**

A person and an agent should be able to inspect, review, and refine the same retained result through a tool's public library and an optional interactive view. Reopening the view should recover existing work, not generate it again. This proposal describes behavioral guarantees to evaluate through small adapters; it does not prescribe a new wire protocol, rendering language, or universal result envelope.

## Fit with the existing specification

The [library remains the capability boundary](../../spec/structure.md). The required thin CLI, provider-free deterministic paths, and Git installation remain unchanged. MCP, a UI, and a background service remain optional; a service starts only when requested. Adding a UI capability that cannot be called from the library remains a defect.

The [v1 manifest](../../spec/manifest.md) remains inert selection information. This proposal adds no frontmatter fields and no required descriptor fields. Hosts must not parse manifest prose or execute `requires.install` as a command. Catalog membership, an installed package, a connected adapter, and an available view are separate facts. Adapter discovery/version metadata needs a separate compatibility decision after implementation evidence.

| Layer | Responsibility |
| --- | --- |
| Smart Tool | Library, domain expertise, optional internal AI, CLI, package and manifest conventions |
| MCP adapter, if supplied | Standard discovery, typed calls, resources, errors, and negotiated capabilities over the library |
| MCP App, if supplied | A portable interactive view using MCP Apps' resource metadata and host bridge |
| Host | Conversation association, granted permissions, rendering, attention, and supported execution services |

MCP does not require intelligence to live in the host: a server can own model calls or negotiate sampling. Internal AI therefore does not distinguish Smart Tools from all MCP servers. The layers are complementary: Smart Tools specifies a package/library shape, while MCP and MCP Apps supply optional interoperability mechanisms. A tool need not know the product hosting its view.

## Proposed scope

Treat **retained work**, **collaborative presentation**, and **execution telemetry** as separable opt-in capabilities. A synchronous tool need not implement operations, a headless tool need not implement views, and unsupported features must remain explicit. The guarantees below apply to capabilities an implementation claims to support; they do not make every feature mandatory for every Smart Tool.

For an MCP adapter, reuse tools with JSON Schemas, resources, and MCP Apps. Use Tasks, elicitation, or sampling only when the specific protocol/extension version and required capability are negotiated. An ordinary tool returning a domain operation handle is valid; it must not claim MCP Tasks support on that basis. No second mandatory JSON-RPC layer is needed.

## Proposed guarantees

### 1. Shared capabilities, explicit authority

Expose presentation actions through public domain methods with equivalent validation, targeting, authority, and receipts. Give portable adapters typed input schemas and documented result shapes; a Python signature string alone cannot drive a generic form. State which actions are deterministic, may invoke a model, or have other external effects. UI adapters do not hide generation or decision logic.

Distinguish verified actor identity, delegated authority, and requested effect. An agent can request a review or perform an authorized edit; it cannot impersonate a human acceptance. Keep substantive actions available through both user and model paths where policy permits. For MCP, declare visibility intentionally; app-only presentation helpers must not become a way around authorization, and a restricted capability must be reported honestly rather than advertised as equivalent.

### 2. Durable identities and mutation receipts

Separate installation/version, retained work, operation, immutable revision, resource, and attached-view identities. Host chat IDs are host metadata, not required domain identifiers. A view reports the revision it actually displays, even when a newer one exists. The tool owns domain state; the host must not maintain a competing revision history.

Mutations target explicit identities and supported state preconditions. Return receipts that distinguish rejection, acceptance, completion, failure, and uncertain execution. Document request-ID deduplication scope and retention; reusing an ID with different arguments must conflict within that scope. Acceptance is not completion, and a lost response is not permission to replay model work. Do not invent atomic concurrency guarantees around a library that cannot enforce them against other callers.

Presenters must preserve the identity and immutable input of an uncertain submission until it is reconciled. Retrying after a lost acknowledgment must not mint a new creative operation or renew its grant; starting new intent is an explicit separate action. Library identity checks must reject collisions with other retained object kinds without replacing their records.

### 3. Observations, navigation, and review

Offer bounded snapshots and scoped references for details. If changes/cursors are supported, identify ordering, truncation, and recovery. Exclude secrets and private reasoning. Selected revision, focused alternative/page, playback position, and saved-draft status are useful semantic observations; they do not imply pixel access.

Treat view context as untrusted observation, not a new instruction, approval, or execution grant. MCP Apps' context updates can convey observations; they are not a durable draft store or a general view-restoration protocol. If shared navigation or draft recovery is supported, implement explicit library operations and define ownership, version/conflict behavior, and restoration through those operations. Do not rely only on browser memory.

Separate inspecting, saving a draft, submitting feedback, requesting refinement, and accepting a result. Feedback retains its target revision and supported anchor. A new revision must not silently move a comment or replace what the user is reviewing. A draft save must not trigger a model call. Preserve unsupported or stale edits with a visible conflict rather than discarding them.

Host-delivered tool results and agent-driven navigation follow the same draft-preservation rules as local navigation. Capture the old revision and draft before awaiting a transition; an outstanding autosave must never write that text onto the newly focused revision.

### 4. Bounded delegated execution

Model-backed mutations require valid authority for their effect, disclosed material, provider configuration, and supported execution limits. A caller may authorize several direct refinements within a finite grant; each submission need not wake the main conversation. Missing or exhausted authority leaves a recoverable request and an actionable explanation.

Advertise enforceable units: model calls, turns, elapsed time, and tokens are not interchangeable with a hard dollar limit. Reject unsupported limits or disclose the downgrade before execution. Credentials stay in a configured environment or credential service, never the view or model-readable state. Package isolation alone does not provide filesystem or network isolation.

### 5. Lifecycle, updates, and forks

Attaching a view, starting an owned runner, taking focus, canceling an operation, finishing work, stopping a service, and deleting retained data are distinct effects. Closing a view only detaches it unless an explicit domain operation says otherwise. Report cancellation acknowledgment separately from terminal cleanup; never stop unrelated processes.

Persist accepted identities and receipts before admitting background work. Reconnect and restart by reading retained state. Do not regenerate to rebuild a view, revive canceled work, or renew expired grants implicitly. Pin active work to a compatible tool version; retained-state migrations and rollback limits must be explicit. Removing an installation must disclose what happens to retained work.

A conversation fork does not imply a domain clone. Carry immutable references through the retained turn boundary; use a read-only attachment until a supported clone/import or a clearly disclosed shared-work attachment is selected. A shared attachment keeps the original object identity and authority checks. Exporting HTML alone is not a full work-state backup.

### 6. Portable presentation and isolation

An MCP App uses a `ui://` HTML resource with `text/html;profile=mcp-app`, advertised through tool `_meta.ui.resourceUri`; resource-specific CSP and permissions belong in the resource's `_meta.ui`. The host grants a supported intersection and reports denied capabilities. Preserve a tool's standalone web security behavior rather than stripping its embedding restrictions.

Give a view a scoped broker, not host credentials, a general app-dispatch handle, or arbitrary filesystem access. Bind calls to the intended server/work and authorized actions; validate schemas, message sources, and stale connections. Tool-authored control UI and generated/imported content have different authority: a simulated prototype button must not invoke real tools or submit decisions. Resources use authorized handles with declared types, size limits, and range semantics when needed; credential-bearing localhost URLs are not a portable transport.

Media makes this boundary concrete. A server can expose retained images, audio, video, or exports through standard MCP resources. The library owns identity, integrity checks, and authorization; the host forwards requests to the bound server rather than dereferencing arbitrary URLs. When a whole resource exceeds the supported message size, a tool may document bounded chunk resources and byte counts. Such URI templates and assembly rules are domain contracts, not a new universal MCP range protocol. An App may assemble a blob for playback and must disclose its own memory/file-size limit. Read-only preview traffic should not repeatedly shift the document, steal focus, or appear as a new conversation event.

A portable view need not reproduce every standalone dashboard feature in its first release. Publish a capability matrix distinguishing library, CLI, MCP tools, and App controls, including prerequisites and omitted operations. Shared actions must preserve semantics where supplied. In particular, an unauthenticated caller field or boolean does not establish human acceptance: omit or explicitly restrict that action until attribution and delegated authority can be represented accurately.

Long-running creation belongs behind the public library's retained operation boundary. A transport adapter cannot make a blocking model call safely resumable merely by returning early or extending its timeout. Reuse an existing owned runner where available, persist admission and its identity, and make polling/cancellation ordinary library capabilities. A transport disconnection must not silently replay that work.

### 7. Progress, accounting, and attention

Expose public stages and durable operation status without claiming unavailable internal reasoning. Attribute known usage to stable model-call and parent-operation identities; distinguish deltas from cumulative totals, estimates from measured values, and price-derived cost from actual billing. Missing token or cost information remains unknown, never zero. Aggregate leaf usage once, including known failed/canceled calls; do not add both a tool subtotal and its children.

Observing a change, notifying a person, and waking an agent are separate effects with host-controlled policy. Deduplicate notifications and continuations. A view-originated refinement has its own operation identity linked to its feedback, not an unrelated current chat turn. Reading, draft autosave, replayed events, and marking attention read do not consume execution authority.

## Evidence required before promoting a profile

Use deterministic intelligence fixtures first. These are proposed acceptance tests, not assertions that implementations already pass them.

| Scenario | Observable evidence |
| --- | --- |
| User and model act on one object | Both paths read the same revision, apply the same validation, and return equivalent receipts; restricted actions remain restricted |
| Provider-free fallback | Import, inspect retained work, and export without a model key or automatic service startup |
| Conflicting edits and drafts | A comment on A stays on A while B arrives; older autosave cannot overwrite a newer draft; conflict policy is enforced in the library |
| Lost response and restart | Repeating an accepted request ID returns its receipt; changed arguments conflict; uncertain paid work is inspected rather than replayed |
| Detach, cancel, and cleanup | Closing/reopening does not generate; cancellation reaches a terminal state or reports unfinished cleanup; unrelated processes survive |
| View and generated-content isolation | Nested generated HTML cannot invoke the broker; stale/config-changed attachments fail; scoped results contain no credentials |
| Media and large resources | Declared byte/type/integrity behavior is enforced; missing, changed, oversized, and interrupted resources produce visible limits rather than arbitrary path access |
| Attribution and partial coverage | A caller cannot self-assert verified human identity; the documented surface matrix matches the actual exposed actions |
| Usage and unsupported features | Missing cost is unknown; totals count each call once; denied device/network capability produces useful feedback |
| Fork and update | Fork cannot silently mutate original work; sharing/clone semantics are explicit; incompatible retained-state migration cannot silently proceed |
| Portability | One tool works in an independent MCP Apps host and headlessly; one host renders an unfamiliar deterministic App without tool-specific code |

## Incremental adoption

Prototype an optional adapter over existing public methods, using a supported MCP SDK (for example Python SDK 2.x) and the official MCP Apps SDK for its view. Keep it an optional package extra where appropriate. Validate with at least two different domains and an independent host before settling profile discovery, mandatory method names, migration rules, or telemetry schemas. SDK versions are implementation choices, not proposed Smart Tool format requirements.

Candidate areas include concept review, slide comments, and timed-media review; each should retain its own domain result shapes. Any implementation PR should state tested capabilities and gaps rather than declare blanket conformance. This proposal changes neither the base conformance kit nor existing manifest validation.

Authoring tools can offer opt-in adapter scaffolds and packaged design guidance while leaving their default scaffold conformant to the current base specification. Generated adapters should start with a deterministic typed library call and an optional self-contained App, require an explicit launch, and include a provider-free transport test. Advisory design checks for this proposal must remain separate from the adopted conformance kit. Catalog discovery can follow the selected tool's installed help for optional surfaces without adding a competing inventory or treating an advertised view as tested host support.

References: [MCP specification](https://modelcontextprotocol.io/specification/latest), [MCP Apps specification and SDK](https://github.com/modelcontextprotocol/ext-apps), [Python MCP SDK](https://py.sdk.modelcontextprotocol.io/), and the existing [Smart Tools roadmap](../../ROADMAP.md).
