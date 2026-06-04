# ADR-0002: Gateway Sidecar Per Hermes Install

## Status

Accepted

## Date

2026-06-04

## Context

The mobile app needs auth, event streaming, approvals, push dispatch, audit logs, and intervention controls. Hermes already owns agent runtime, tools, browser, memory, skills, and voice surfaces.

## Decision

Run a Hermes Control Gateway beside each Hermes install. The gateway is the mobile-facing sidecar and policy boundary.

## Consequences

Positive:

- Keeps self-hosted control local.
- Allows one gateway per node and many-node mobile inventory.
- Separates mobile safety/control concerns from core Hermes runtime.
- Gives teams a clear backend boundary.

Negative:

- Requires Hermes integration adapters.
- Gateway and Hermes version compatibility must be managed.
- Each node has its own local state and audit store unless a future aggregator is added.

## Follow-Up

- Define adapter contracts for Hermes sessions, tools, browser, voice, and events.
- Add gateway compatibility metadata to node inventory.
