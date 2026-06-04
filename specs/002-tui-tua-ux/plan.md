# Implementation Plan: TUI, TUA, Teams, And Advanced Approval UX

**Branch**: `001-hermes-mobile-command` | **Date**: 2026-06-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-tui-tua-ux/spec.md`

## Summary

Define the next major mobile operator UX layer for Hermes Mobile Control Plane: advanced approval actions, TUA assistance workflows, real TUI terminal workflows, Teams grouping, and a five-tab mobile navigation model. This plan is documentation-first and prepares future implementation slices for gateway contracts, mobile UI, and Hermes integration.

## Technical Context

**Language/Version**: Existing gateway uses Python/FastAPI; mobile shell uses Flutter/Dart. This sprint does not add production implementation.

**Primary Dependencies**: Existing OpenAPI, docs, Spec Kit feature structure, and architecture documents.

**Storage**: Planned entities extend the existing local gateway data model and remain storage-engine neutral in this sprint.

**Testing**: Documentation validation, OpenAPI YAML parsing, docs link checks, placeholder scan, `specify check`, and existing gateway tests if API contract changes.

**Target Platform**: Native iOS/Android mobile app and self-hosted Hermes Control Gateway.

**Project Type**: Mobile app plus local gateway control-plane service.

**Performance Goals**: Future TUI should feel interactive on mobile; future TUA and approval screens should resolve user context quickly. Exact latency budgets belong in implementation slices.

**Constraints**: Self-hosted first, Tailscale first, signed device decisions, fail-closed approvals, local audit logging, no required public exposure.

**Scale/Scope**: One node must remain useful; many nodes and many agents must be organized through Agents and optional Teams.

## Constitution Check

The current constitution file still contains template placeholders and does not define enforceable project gates. Existing project constraints from accepted ADRs apply:

- Tailscale-first self-hosted connectivity.
- Gateway sidecar per Hermes install.
- Device key pairing and signed approvals.
- WebSocket primary event stream.
- Push notifications are hints, not durable state.
- Approval engine fails closed.
- Local append-only audit log.

## Project Structure

### Documentation

```text
specs/002-tui-tua-ux/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/
    └── requirements.md

docs/
├── architecture/
│   ├── tui-architecture.md
│   ├── tua-architecture.md
│   ├── advanced-approval-actions.md
│   └── teams-agent-grouping.md
├── adr/
│   ├── 0012-tui-first-class-mobile-subsystem.md
│   ├── 0013-tua-separate-assistance-subsystem.md
│   ├── 0014-agents-v1-terminology-teams-grouping.md
│   └── 0015-modified-conditional-approval-decisions.md
├── api/openapi.yaml
├── data-model.md
└── mobile-ux-architecture.md
```

### Source Code

No production code is required in this sprint. Future implementation slices will touch:

```text
gateway/src/hermes_gateway/
gateway/tests/
mobile/lib/src/
```

**Structure Decision**: Keep this sprint documentation-first. OpenAPI and data model updates may define planned contracts, but gateway/mobile runtime behavior should wait for dedicated implementation slices.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| TUI as a first-class subsystem | Real mobile intervention requires interactive terminal control | Treating terminal as logs would not support recovery or Git workflows |
| TUA as a separate assistance subsystem | Help requests and collaborative clarification need state beyond approval cards | Overloading approval states would blur chat, assistance, and decision records |
| Teams as optional grouping | Multiple nodes and agents need organization | Replacing nodes/agents with Teams would hide source identity |
| Modified approval responses | Users need partial approvals and constraints | Binary approve/deny creates unsafe over-approval pressure |
