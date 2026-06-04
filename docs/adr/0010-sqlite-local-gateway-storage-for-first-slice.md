# ADR-0010: SQLite Local Gateway Storage For First Slice

## Status

Accepted

## Date

2026-06-04

## Context

The first executable Hermes Control Gateway slice needs durable local records for pairing, devices, events, approvals, notifications, and audit logs. The approved architecture is self-hosted first and does not require hosted infrastructure.

## Decision

Use SQLite as the first gateway persistence layer. The gateway stores local records in a single SQLite database path configured by `HERMES_GATEWAY_DB`.

## Consequences

Positive:

- Keeps the first slice self-hosted and easy to run.
- Avoids external database setup.
- Supports local audit/event persistence and test isolation.
- Can later migrate to Postgres or another durable store behind the same repository boundary.

Negative:

- Not suitable for distributed multi-writer gateway deployments.
- Requires explicit backup/export planning for production self-hosted use.
- Enterprise deployments may need a different persistence backend.

## Follow-Up

- Define migration strategy before broad production use.
- Add audit export and backup guidance.
- Keep SQL access isolated behind the gateway store module.
