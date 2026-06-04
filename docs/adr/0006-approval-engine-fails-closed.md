# ADR-0006: Approval Engine Fails Closed

## Status

Accepted

## Date

2026-06-04

## Context

Hermes may request consequential actions such as shell execution, browser submission, file deletion, email sending, repo push, payment, credential access, and network scanning. Approval failures must not allow unsafe execution.

## Decision

The approval engine fails closed. Expired, malformed, unavailable, replayed, invalidly signed, policy-denied, or unauditable approvals are rejected and the requested action does not proceed.

## Consequences

Positive:

- Safer default for permissive or semi-autonomous agents.
- Clear security posture for mobile approvals.
- Reduces ambiguity during outages.

Negative:

- Agents may block more often during gateway/mobile issues.
- Users need good UX for expiry and blocked states.
- Policy configuration must avoid excessive false positives.

## Follow-Up

- Define risk policy defaults.
- Build clear mobile states for expired, cancelled, and denied approvals.
