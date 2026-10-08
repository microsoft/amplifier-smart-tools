# Using samplegood

Every invocation writes exactly one JSON document to stdout. Diagnostics, when
there are any, go to stderr and never share the result stream.

A success carries `result`:

```json
{"result": {"chars": 11, "words": 2, "lines": 1}}
```

A failure carries `error`, with a machine-readable `code`, a `message`, and a
`remedy` naming what to do about it:

```json
{"error": {"code": "no_provider", "message": "...", "remedy": "Set SAMPLE_PROVIDER_KEY ..."}}
```

Exit codes: `0` success, `2` bad invocation (unknown capability, no capability
named, unrecognised flag), `3` a model-backed capability with no provider
configured. A failure is never reported with exit code 0.

## Configuring the provider

`summarize` is model-backed. Set `SAMPLE_PROVIDER_KEY` to a valid provider credential.
Without it, `summarize` exits 3 with a `no_provider` envelope and never falls back to a
deterministic answer. `stats` needs no provider.
