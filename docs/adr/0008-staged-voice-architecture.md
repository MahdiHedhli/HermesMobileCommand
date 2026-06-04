# ADR-0008: Staged Voice Architecture

## Status

Accepted

## Date

2026-06-04

## Context

Hermes has voice capabilities and the mobile product should eventually support live voice mode. Full-duplex voice and WebRTC are valuable but add substantial complexity.

## Decision

Ship voice in stages: push-to-talk first, half-duplex second, full-duplex/WebRTC third. Voice approvals must use the same approval framework and require a confirmation phrase.

## Consequences

Positive:

- Voice can start with a simpler mobile and gateway path.
- Core control plane work is not delayed by media complexity.
- Future providers such as Hermes voice mode, XTTS, OmniVoice, or others can sit behind a gateway adapter.

Negative:

- MVP voice is less immersive.
- Provider adapter design is still needed.
- Full-duplex will require later signaling and media work.

## Follow-Up

- Define voice provider adapter contract.
- Add voice audit events and transcript redaction rules.
