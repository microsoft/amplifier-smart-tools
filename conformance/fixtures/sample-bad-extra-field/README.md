# samplegood

A minimal reference smart tool used as the conformance kit's known-good fixture.

## Capabilities

- `stats --text TEXT` -- deterministic. Runs with no model provider configured.
- `summarize --text TEXT` -- model-backed. Requires a provider.

## Configuring the provider

The `summarize` capability is model-backed. Set `SAMPLE_PROVIDER_KEY` to a valid
provider credential to enable it. With no provider configured, `summarize` fails
loudly and names this remedy; it never silently degrades to a deterministic
answer.
