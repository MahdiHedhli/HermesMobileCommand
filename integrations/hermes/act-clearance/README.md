# act-clearance — Hermes ↔ ACT control-plane bridge

An in-process Hermes plugin that makes the operator's paired Secure-Enclave phone a
first-class control surface for the real Hermes agent. Three planes:

- **Monitoring** — session/tool lifecycle hooks upsert the real agent / session / mission
  into ACT (`POST /v1/runtime/context`) so the app's dashboard / agents / task-visibility
  show the **real** agent live.
- **Clearance** — risky tools raise an ACT clearance via `pre_tool_call` and **block**
  until approved on the phone (fail-closed on deny/expiry/timeout/gateway error).
- **Interactive questions** — designated "ask" tools (`clarify`) raise an ACT TUA request
  and block until the operator answers on the phone; the operator's typed reply is
  returned to the agent.

Default-OFF: every hook is a no-op unless `ACT_CLEARANCE_ENABLED=1` (and the plugin is in
Hermes `plugins.enabled`), so installing the files cannot disrupt a live agent.

See [docs/implementation/act-010-hermes-control-bridge.md](../../../docs/implementation/act-010-hermes-control-bridge.md)
(bridge) and [act-009](../../../docs/implementation/act-009-hermes-clearance-plugin.md)
(clearance) for design + verification.

## Install

```sh
cp -r integrations/hermes/act-clearance ~/.hermes/plugins/act-clearance
hermes plugins enable act-clearance          # adds it to plugins.enabled (opt-in)
```

## Run (default-off until you set the env gate)

```sh
ACT_CLEARANCE_ENABLED=1 \
ACT_GATEWAY_URL=http://127.0.0.1:8788/v1 \
ACT_CLEARANCE_AGENT_ID=colpanic_m2 \
ACT_CLEARANCE_AGENT_NAME=ColPanicM2 \
ACT_QUESTION_TOOLS=clarify \
hermes ...
```

Without `ACT_CLEARANCE_ENABLED=1` the hook is a no-op, so the plugin cannot affect an
agent that has not opted in. See the doc for all config env vars.
