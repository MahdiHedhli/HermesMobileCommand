# ADR-0007: Local Append-Only Audit Log

## Status

Accepted

## Date

2026-06-04

## Context

Approvals, push notifications, interventions, device changes, and policy decisions need forensic review. Self-hosted operation should not depend on a hosted audit service.

## Decision

Each Hermes Control Gateway maintains a local append-only, hash-chained audit log. Audit events are generated for auth, approval, notification, intervention, policy, event-stream, and voice lifecycle events.

## Consequences

Positive:

- Works without public cloud dependencies.
- Gives operators local ownership of audit data.
- Supports threat review and incident investigation.
- Hash chaining improves tamper evidence.

Negative:

- Local host compromise can still affect audit storage.
- Cross-node audit aggregation is not solved in MVP.
- Retention and export need clear configuration.

## Follow-Up

- Define audit event schema and retention defaults.
- Add local export before enterprise aggregation.
