# ADR-0004: WebSocket Primary Event Stream

## Status

Accepted

## Date

2026-06-04

## Context

The mobile app needs live agent activity, session updates, approval updates, and notification reconciliation. Candidate transports include WebSocket, SSE, MQTT, and WebRTC data channels.

## Decision

Use WebSocket as the primary live event stream, paired with REST cursor-based backfill. Use WebRTC later for voice or live browser/screen media when needed.

## Consequences

Positive:

- Good mobile support.
- Bidirectional enough for stream controls and heartbeats.
- Lower operational overhead than MQTT.
- Simpler than WebRTC for core events.

Negative:

- Mobile backgrounding can interrupt connections.
- Gateway must implement cursoring and backfill.
- High-frequency terminal/browser events need coalescing.

## Follow-Up

- Implement event envelope, cursor, retention, and reconnect semantics.
- Define coalescing rules for terminal output and browser state.
