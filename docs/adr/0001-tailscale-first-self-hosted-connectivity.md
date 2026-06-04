# ADR-0001: Tailscale-First Self-Hosted Connectivity

## Status

Accepted

## Date

2026-06-04

## Context

Hermes Mobile Control Plane must support self-hosted Hermes installs without requiring public internet exposure. Users may run Hermes on homelab machines, laptops, VPS hosts, workstations, and work VMs. Mobile access needs secure reachability, but the project should avoid hosted dependencies unless clearly justified.

## Decision

Default connectivity is Tailscale-first. Trusted local network access is acceptable for self-hosted use. HTTPS and hosted relay access are future optional paths, not launch requirements.

## Consequences

Positive:

- No public exposure required.
- Fits homelab and self-hosted operators.
- Reduces need for a central SaaS control plane.
- Works with one node and later many nodes.

Negative:

- Users must install/configure Tailscale or provide local reachability.
- Mobile app must handle unreachable nodes gracefully.
- Non-technical users may need the future relay path.

## Follow-Up

- Define gateway URL discovery and pairing UX for Tailscale addresses.
- Keep API contracts relay-compatible without requiring relay implementation.
