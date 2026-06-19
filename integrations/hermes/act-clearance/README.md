# act-clearance — Hermes plugin

Gates risky Hermes tool calls through the Agentic Control Tower (ACT) for operator
approval on a paired Secure-Enclave phone. Registers a `pre_tool_call` hook that raises
an ACT clearance and **blocks** the tool until approved (fail-closed on
deny/expiry/timeout/gateway error).

See [docs/implementation/act-009-hermes-clearance-plugin.md](../../../docs/implementation/act-009-hermes-clearance-plugin.md)
for design + verification.

## Install

```sh
cp -r integrations/hermes/act-clearance ~/.hermes/plugins/act-clearance
hermes plugins enable act-clearance          # adds it to plugins.enabled (opt-in)
```

## Run (default-off until you set the env gate)

```sh
ACT_CLEARANCE_ENABLED=1 \
ACT_GATEWAY_URL=http://127.0.0.1:8788/v1 \
hermes ...
```

Without `ACT_CLEARANCE_ENABLED=1` the hook is a no-op, so the plugin cannot affect an
agent that has not opted in. See the doc for all config env vars.
