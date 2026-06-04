# ADR-0013: TUA As Separate Assistance Subsystem

## Status

Accepted

## Date

2026-06-04

## Context

Agents may need help from the user before continuing. The user may also need more information, partial approval, terminal context, browser context, or a modified directive before returning control. Ordinary chat is too broad, and approval records are too narrow to model this workflow cleanly.

## Decision

Create TUA as a separate subsystem. TUA means Take User Assistance and represents bounded user-agent assistance sessions with explicit states, messages, context attachments, and return-control handoffs.

TUA can be opened from approvals, Inbox, Live Activity, Agent Detail, Missions, notifications, terminal context, or browser context.

## Consequences

Positive:

- Assistance can be audited independently from ordinary chat and approvals.
- Agents receive explicit return-control summaries instead of inferring intent from chat.
- TUA can coordinate More Info, partial approval, TUI, and browser assistance without overloading approval state.

Negative:

- Adds new durable entities and event types.
- Requires careful UX to avoid confusing TUA chat with general Hermes chat.
- Linked approvals must remain pending until explicitly resolved.

## Follow-Up

- Implement assistance request/session/message models.
- Define return-control payload validation.
- Add E2E smoke coverage for request-to-return-control.
