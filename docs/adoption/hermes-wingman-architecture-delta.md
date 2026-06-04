# Hermes Wingman Architecture Delta

## Purpose

This document compares hermes-wingman with Hermes Mobile Control Plane and prevents adoption drift.

Hermes Wingman is a broad GUI replacement for Hermes Agent. Hermes Mobile Control Plane is a Tailscale-first mobile safety and intervention layer.

## Architecture Summary

| Area | hermes-wingman | Hermes Mobile Control Plane |
| --- | --- | --- |
| Product role | Desktop/mobile/web GUI replacement for Hermes CLI and setup | Mobile control plane for secure access, approvals, push, intervention, multi-agent operations |
| Primary user value | "No terminal needed" full GUI parity | "My agent is about to do something consequential; I can approve, redirect, or stop it" |
| Default connectivity | README describes LAN mobile access and subnet scanning; backend code binds localhost in inspected commit | Tailscale-first, explicit pairing, no public exposure required |
| Backend shape | Single Rust Axum backend on port 9120, plus Rails web proxy/dashboard | Hermes Control Gateway beside each Hermes node, with device auth, event stream, approval engine, push, audit |
| Web/desktop scope | Desktop, mobile, and Rails web dashboard | Native mobile-first; web portal parity only where needed for control/safety |
| Agent model | Mostly one backend/Hermes runtime with broad GUI panels | Multiple registered Hermes nodes and agents with explicit inventory, tags, health, capabilities |
| Security model | No gateway auth middleware observed; permissive CORS; provider and config endpoints | Device pairing, device-bound tokens, signed approvals, scoped interventions, audit log |
| Action model | Ordinary GUI actions: config edit, file edit, CLI proxy, gateway start/stop | Safety-scoped actions: approve/deny, pause, kill task, quarantine, inject instruction |
| Provider model | Direct provider calls and provider key/OAuth management in backend | Hermes-mediated actions; mobile app does not manage raw provider secrets in MVP |
| File/config model | Direct config YAML editor and broad filesystem browser | Read-only/redacted summaries first; mutations require approval and scoped policy |
| Live activity | Logs, sessions, SSE chat, planned live tool overlays | Event stream with cursor/backfill, live plan/tool/target, approvals, interventions, browser state |
| Voice | Not a core inspected implementation path | Staged voice architecture: push-to-talk, half-duplex, full-duplex/WebRTC later |

## LAN-First vs Tailscale-First

hermes-wingman:

- README says mobile auto-discovers a backend on LAN by scanning subnet hosts on port 9120.
- Flutter client has LAN discovery code that attempts common hosts on the local subnet.
- Desktop startup attempts to set `BIND_ADDR=0.0.0.0:9120`.
- Rust backend code inspected binds to `127.0.0.1:9120`, creating a doc/code mismatch.

Hermes Mobile Control Plane:

- Uses Tailscale as the default private connectivity path.
- Requires explicit node pairing before trust.
- Does not scan arbitrary LAN hosts.
- Treats local network access as acceptable but not auto-trusted.
- Supports optional future relay without making it required.

Adoption decision:

- Reject LAN scanning.
- Adapt the idea of connection status and fallback manual URL entry into a Tailscale node registry/pairing model.

## GUI Replacement vs Control Plane

hermes-wingman:

- Replaces setup, config editing, provider login, file browsing, cron, gateway setup, and model switching.
- Optimizes for replacing CLI workflows across desktop/mobile/web.

Hermes Mobile Control Plane:

- Does not aim to replace every Hermes admin workflow.
- Focuses on mobile access where the operator needs situational awareness, push alerts, approvals, and intervention.
- Keeps setup/config/provider management out of MVP unless it directly supports safety.

Adoption decision:

- Use Wingman screens as inventory of Hermes surfaces.
- Do not copy full GUI replacement scope into this product.

## Single Backend vs Multi-Agent Registry

hermes-wingman:

- One backend service exposes one Hermes home/runtime context.
- Sessions and agents are not strongly namespaced by multiple nodes in the inspected mobile UX.

Hermes Mobile Control Plane:

- Each Hermes install has a gateway.
- Mobile app manages many nodes.
- All sessions, agents, approvals, notifications, and audit records are node-scoped.

Adoption decision:

- Adapt session/status/log models only after adding `node_id`, `agent_id`, capability, health, and last-seen semantics.

## Ordinary GUI Actions vs Signed Approvals

hermes-wingman:

- UI actions call REST endpoints directly.
- Backend exposes config write, file write/delete, CLI command, provider auth, gateway service toggles.
- No signed decision model observed.

Hermes Mobile Control Plane:

- Consequential actions require signed device decisions.
- Approval requests bind action, risk, scope, payload hash, node, agent, session, and expiry.
- Emergency controls are signed and audited.

Adoption decision:

- Reject direct mutation endpoints.
- Adapt UI affordances only after routing through approval/intervention framework.

## Local Config/File Management vs Safety-Scoped Intervention

hermes-wingman:

- Config editor writes full YAML.
- File handler allows absolute paths and navigation outside `~/.hermes`.
- File delete can remove directories recursively.

Hermes Mobile Control Plane:

- Mobile file/config views should be read-only and redacted by default.
- Mutations are scoped to sessions/artifacts or explicit approval requests.
- Destructive file operations are high or critical risk.

Adoption decision:

- Reject direct file/config management.
- Adapt only safe artifact viewer and redacted config summary concepts.

## Direct Provider Calls vs Hermes-Mediated Actions

hermes-wingman:

- Backend can call providers directly for chat/model probing and uses API keys from config.
- OAuth providers fall back to Hermes CLI.
- Provider setup and API-key entry are GUI features.

Hermes Mobile Control Plane:

- Mobile does not become a provider admin or model router.
- Hermes remains the authority for provider use.
- Mobile may display model/provider status as context, but provider mutations are out of MVP.

Adoption decision:

- Reject direct provider calls and raw provider key workflows.
- Adapt model/provider visibility as read-only status where useful.

## Web/Desktop Parity vs Mobile-First Safety UX

hermes-wingman:

- Desktop sidebar and web dashboard cover many admin screens.
- Mobile bottom nav compresses a broad GUI into a smaller surface.

Hermes Mobile Control Plane:

- Mobile UX should prioritize Dashboard, Agents, Live Activity, Approvals, Notifications, Voice, and Settings.
- Emergency controls must be visible from active task and approval contexts.
- Web portal parity is subordinate to safety and intervention.

Adoption decision:

- Adapt selected screen patterns but rebuild navigation around safety.

## Net Delta

Hermes Wingman is most useful as:

- Feature inventory for Hermes GUI surfaces.
- Reference for sessions/logs/skills/memory/files/gateway platform concepts.
- Evidence of unsafe patterns to avoid for mobile remote control.
- Inspiration for a typed client and route taxonomy.

Hermes Wingman should not be used as:

- A fork base.
- A direct mobile backend.
- A security model.
- A LAN discovery model.
- A file/config/provider admin surface for HermesMobileCommand MVP.
