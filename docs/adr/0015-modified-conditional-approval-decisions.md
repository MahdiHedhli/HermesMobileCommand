# ADR-0015: Modified And Conditional Approval Decisions

## Status

Accepted

## Date

2026-06-04

## Context

Binary approve/deny decisions are sometimes too blunt. Users may want to approve only part of a request, add constraints, replace the action, ask for more information, open TUA, open TUI, or create a durable policy. Without a formal model, users are pushed toward unsafe broad approvals or out-of-band chat instructions.

## Decision

Support modified and conditional approval decisions through an `ApprovalResponse` model. Keep `ApprovalRequest.state` compact where practical, and store richer user intent in response records.

Approval responses may include:

- decision type
- user message
- replacement action
- constraints
- approved scope
- policy creation flag
- expiry
- deciding device
- decision timestamp

Approve Forever is treated as policy creation or policy proposal and requires a second confirmation.

## Consequences

Positive:

- Users can express safer alternatives.
- Gateway can audit precise intent instead of only final state.
- TUA and TUI escalation can be modeled without pretending they are approvals.

Negative:

- Hermes must evaluate modified instructions and constraints before proceeding.
- Policy proposal and permanent approval UX need strong warning and revocation flows.
- More response types require careful mobile state design.

## Follow-Up

- Implement `ApprovalResponse`, `ApprovalConstraint`, and `ApprovalPolicy`.
- Add gateway policy checks for constraints and replacement actions.
- Add mobile flows for More, Other, More Info, and Approve Forever confirmation.
