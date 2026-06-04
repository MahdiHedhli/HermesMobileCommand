# ADR-0014: Agents V1 Terminology With Teams Grouping

## Status

Accepted

## Date

2026-06-04

## Context

The mobile app needs simple navigation for one or many Hermes installs. Users reason about active workers as agents, while nodes and gateways remain important source identity. As the number of agents grows, users also need grouping.

## Decision

Use "Agents" as the primary v1 UI term and tab. Add Teams as an optional grouping layer for agents. Teams do not replace node, gateway, agent, or session identity.

The v1 tab model is:

- Home
- Agents
- Missions
- Voice
- Inbox

## Consequences

Positive:

- The primary navigation term matches what users control.
- Single-node users are not forced into grouping setup.
- Multi-node users can organize agents while preserving source context.

Negative:

- Missions needs a clear future mapping to Hermes sessions/tasks.
- Teams add another metadata layer to keep synchronized.
- UI must consistently disambiguate agents with the same name on different nodes.

## Follow-Up

- Implement Team and AgentTeamMembership planned models.
- Add Home and Agents rollup behavior.
- Define how Missions maps to Hermes sessions, tasks, and artifacts.
