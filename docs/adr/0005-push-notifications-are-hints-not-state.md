# ADR-0005: Push Notifications Are Hints, Not Durable State

## Status

Accepted

## Date

2026-06-04

## Context

Mobile users need urgent alerts for approvals, blocked agents, security alerts, task completion, health, and voice callbacks. APNs and FCM are unavoidable platform dependencies for push delivery, but delivery is best effort and OS-controlled.

## Decision

Push notifications are wake-up hints. Durable notification, approval, and session state lives in the gateway and audit log. Push payloads contain only secret-free text and opaque references.

## Consequences

Positive:

- Avoids relying on OS delivery guarantees.
- Reduces secret leakage through notification surfaces.
- Keeps approvals anchored to gateway state.
- Supports notification dedupe and audit.

Negative:

- Mobile app must fetch current state after notification open.
- Some notifications may not display due to OS settings.
- Push provider integration is still required.

## Follow-Up

- Implement secret scanning before dispatch.
- Add notification audit events and delivery reconciliation.
