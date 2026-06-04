# ADR-0012: TUI As First-Class Mobile Subsystem

## Status

Accepted

## Date

2026-06-04

## Context

Hermes Mobile Control Plane is becoming a mobile operator surface, not only a chat and approval app. Operators sometimes need direct terminal control to inspect state, recover work, run commands, edit files, or complete tasks from mobile. A log viewer cannot support these workflows.

## Decision

Treat TUI as a first-class subsystem. TUI means Text User Interface and must support real terminal sessions, terminal attach/detach, terminal I/O streaming, mobile key entry, copy/paste workflows, and agent-aware context.

TUI must remain subject to signed device authorization, gateway policy, and local audit logging.

## Consequences

Positive:

- Mobile can support real intervention and recovery workflows.
- Terminal sessions can be linked to approvals, TUA, agents, sessions, and audit records.
- The product has a clear path to mobile Git workflows and tmux-oriented operation.

Negative:

- PTY and mobile terminal UX add non-trivial implementation complexity.
- Paste handling and terminal retention need careful safety policy.
- Terminal streams may contain sensitive content and require redaction/retention discipline.

## Follow-Up

- Define terminal attach token behavior.
- Implement a minimal PTY/tmux proof of concept in a dedicated slice.
- Add mobile terminal accessibility and keyboard tests.
