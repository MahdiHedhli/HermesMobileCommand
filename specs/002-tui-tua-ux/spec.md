# Feature Specification: TUI, TUA, Teams, And Advanced Approval UX

**Feature Branch**: `001-hermes-mobile-command`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Draft and integrate the next major product specification for Hermes Mobile Control Plane covering TUI, TUA, advanced approval actions, agent grouping by Teams, and mobile-first operator UX."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolve Advanced Approvals Safely (Priority: P1)

As a mobile Hermes operator, I want approval cards to support approve, deny, more info, modified instructions, partial approval, terminal escalation, and assistance escalation so I can make precise decisions without losing safety context.

**Why this priority**: Approval and intervention are the core mobile differentiators. Advanced decisions must improve safety rather than turn every risky action into a binary choice.

**Independent Test**: Can be tested by presenting approval requests for different risk levels and confirming the user can resolve each with approve, deny, more info, modified instructions, TUA escalation, TUI escalation, pause agent, stop task, or stop agent while preserving audit context.

**Acceptance Scenarios**:

1. **Given** a pending approval, **When** the user opens the approval card, **Then** the primary actions are Approve, Deny, and More with node, agent, session, risk, expiry, and summary visible.
2. **Given** the user opens More, **When** the menu appears, **Then** it includes Approve Once, Approve For Session, Approve For Agent, Approve Forever, Other, More Info, Open TUA Session, Open TUI Session, Pause Agent, Stop Task, and Stop Agent.
3. **Given** the user chooses Approve Forever, **When** the approval is high or critical risk, **Then** the app shows a second warning screen, explains the policy consequence, and prevents Approve Forever from being the default action.
4. **Given** the user chooses Other, **When** they submit alternate instructions, partial approval, replacement action, or constraints, **Then** Hermes receives a modified approval response and the audit log records the modification.
5. **Given** the user chooses More Info, **When** the detail view opens, **Then** the user sees a friendly summary first and can explicitly drill into technical detail or raw redacted payload.

---

### User Story 2 - Get Help Through TUA (Priority: P2)

As a Hermes operator, I want a Take User Assistance session when an agent asks for help or when I need more context, so I can collaborate with the agent, inspect relevant state, adjust the directive, and return control cleanly.

**Why this priority**: TUA turns approval from a one-shot modal into an assistance workflow. It is the bridge between passive review and active mobile intervention.

**Independent Test**: Can be tested by emitting an assistance request, opening a TUA session, exchanging messages, attaching approval context, opening terminal or browser assistance, and returning control to the agent with a user-written summary.

**Acceptance Scenarios**:

1. **Given** an agent requests help, **When** the user opens the request from Inbox or an approval, **Then** the TUA session shows agent, node, session, reason, current state, and safe next actions.
2. **Given** a TUA session is active, **When** the user asks for more information, **Then** the agent can respond inside the assistance context without executing the blocked action.
3. **Given** the user modifies the directive, **When** they return control, **Then** Hermes receives the user summary, constraints, and resume instruction.
4. **Given** the user needs deeper context, **When** they open TUI or browser assistance from TUA, **Then** the assistance session remains linked to the original agent/session and approval.

---

### User Story 3 - Operate A Real Mobile TUI (Priority: P3)

As a mobile Hermes operator, I want a real terminal interface, not just a log viewer, so I can inspect, edit, run, and recover work from mobile when Hermes needs hands-on intervention.

**Why this priority**: A mobile control plane becomes materially more useful if the operator can complete real terminal workflows without switching to a laptop.

**Independent Test**: Can be tested by attaching to a terminal session and completing a mobile Git workflow: inspect status, review diff, edit a file, run tests, commit, and push.

**Acceptance Scenarios**:

1. **Given** a terminal session exists for an agent/session, **When** the user opens TUI, **Then** they can attach, detach, send keys, paste safely, and close the session.
2. **Given** the user uses mobile copy/paste, **When** they paste multi-line content, **Then** the app offers paste-only, paste-and-execute, and paste-as-file behavior where applicable.
3. **Given** the user needs shell control keys, **When** they open the accessory bar, **Then** they can access ESC, TAB, CTRL, ALT, CMD, arrows, shell symbols, brackets, function keys, Home, End, PgUp, and PgDn.
4. **Given** the user attaches from iPad or with an external keyboard, **When** they use the terminal, **Then** the layout supports larger viewports and physical keyboard input.

---

### User Story 4 - Navigate Agents And Teams (Priority: P4)

As a user with multiple Hermes nodes and agents, I want Agents to be the primary v1 term and Teams to be an optional organizing layer so I can browse by work context without confusing source nodes or active tasks.

**Why this priority**: The mobile app must remain understandable as the number of nodes and agents grows. Teams help organize without replacing the underlying agent and node identity model.

**Independent Test**: Can be tested by registering multiple nodes, assigning agents to Teams, viewing Agents and Home tabs, and confirming every action still shows node/source context.

**Acceptance Scenarios**:

1. **Given** the user opens Agents, **When** multiple agents are registered, **Then** the list can show individual agents, Team groupings, node/source context, capabilities, status, active task, pending approvals, and recent notifications.
2. **Given** Teams are configured, **When** the user filters by Team, **Then** agents remain traceable to their source node and gateway.
3. **Given** no Teams exist, **When** the user opens Agents, **Then** the app still works as an individual agent list.
4. **Given** an agent has active approvals or notifications, **When** it appears inside a Team, **Then** badges and counts reflect the agent state without hiding the node context.

---

### User Story 5 - Use Mobile-First Operator Navigation (Priority: P5)

As a mobile operator, I want the app organized around Home, Agents, Missions, Voice, and Inbox so active operational work, approvals, assistance, voice, and notifications are easy to reach.

**Why this priority**: TUI, TUA, Teams, and advanced approvals need a coherent navigation model before polished UI work begins.

**Independent Test**: Can be tested by walking through the five-tab navigation model and confirming each tab has a clear purpose, primary content, and safety-relevant deep links.

**Acceptance Scenarios**:

1. **Given** the app launches, **When** the user reaches Home, **Then** they can see operational state and urgent items across registered nodes.
2. **Given** the user opens Inbox, **When** approvals, assistance requests, notifications, and callbacks exist, **Then** they are grouped by urgency and durable state.
3. **Given** the user opens Missions, **When** active or recent mission/task contexts exist, **Then** they can navigate to live activity, TUA, TUI, approvals, and artifacts.
4. **Given** the user opens Voice, **When** voice is not fully implemented, **Then** the screen still aligns with future voice intervention and callback flows without blocking non-voice workflows.

### Edge Cases

- A user opens a TUI session while the underlying agent is paused or blocked.
- A TUA session is requested, but the mobile app is offline.
- The user starts Approve Forever and the approval expires before final confirmation.
- A modified approval response conflicts with gateway policy.
- A terminal paste contains secrets, control characters, or multi-line commands.
- A Team includes agents from unreachable nodes.
- An assistance session is closed while a linked approval remains pending.
- A raw redacted payload is large enough to make mobile review difficult.
- A user attempts to stop an agent from a Team context where multiple agents share a display name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The mobile app MUST use "Agents" as the primary v1 term for Hermes agent browsing and control.
- **FR-002**: The mobile app MUST support optional Teams grouping for agents without requiring Teams for single-agent or single-node users.
- **FR-003**: The v1 tab model MUST include Home, Agents, Missions, Voice, and Inbox.
- **FR-004**: The Agents tab MUST show individual agents, optional Teams grouping, node/source context, capabilities, current status, active task, pending approval count, and recent notification count.
- **FR-005**: Approval cards MUST expose primary actions Approve, Deny, and More.
- **FR-006**: The More approval menu MUST include Approve Once, Approve For Session, Approve For Agent, Approve Forever, Other, More Info, Open TUA Session, Open TUI Session, Pause Agent, Stop Task, and Stop Agent.
- **FR-007**: Approve Forever MUST require a second confirmation screen and MUST create or propose an approval policy record.
- **FR-008**: Approve Forever MUST NOT be the default action for high or critical risk approvals.
- **FR-009**: Other approval responses MUST allow alternate instructions, partial approval, replacement action, and explicit constraints.
- **FR-010**: More Info MUST present a friendly summary first, allow technical drill-down, allow TUA interaction, and require explicit expansion before showing raw redacted payload.
- **FR-011**: Approval responses MUST support decision types for approve, deny, modified response, needs info, TUA escalation, TUI escalation, pause agent, stop task, and stop agent.
- **FR-012**: Approval response records MUST include decision type, optional user message, optional replacement action, constraints, approved scope, policy creation flag, expiry, deciding device, and decision timestamp.
- **FR-013**: TUI MUST be specified as a real terminal experience rather than a log viewer.
- **FR-014**: TUI MUST support terminal session attach, detach, close, terminal I/O streaming, key events, paste payloads, copy workflows, and terminal context linked to agent/session.
- **FR-015**: TUI MUST support a mobile special key accessory bar with pages for control keys, shell symbols, brackets, function keys, and navigation keys.
- **FR-016**: TUI MUST support mobile copy/paste workflows including one-tap copy for commands, paths, URLs, logs, and errors.
- **FR-017**: TUI MUST support multi-line paste handling, paste-and-execute, and paste-as-file options.
- **FR-018**: TUI MUST support iPad layout, external keyboard input, and Android keyboard behavior.
- **FR-019**: TUA MUST support agent assistance requests, assistance chat, more-info drill-down, partial approvals, modified directives, terminal assistance, browser assistance, pause/resume, return control, and user summary on resume.
- **FR-020**: TUA session states MUST include requested, active, waiting_on_user, user_controlling, returned_to_agent, closed, and cancelled.
- **FR-021**: Teams APIs and data models MUST support listing Teams, creating Teams, assigning agents to Teams, and removing agents from Teams.
- **FR-022**: TUI APIs and data models MUST support creating, attaching, detaching, closing, streaming I/O, sending key events, and sending paste payloads.
- **FR-023**: TUA APIs and data models MUST support creating assistance requests, listing assistance requests, opening sessions, sending messages, attaching terminal or browser context, returning control, and closing sessions.
- **FR-024**: All approval, TUI, and TUA actions that affect agent execution MUST be audit logged with node, agent, session, device, and user context where available.
- **FR-025**: TUI and TUA entry points MUST preserve node, agent, session, and approval context when launched from an approval, mission, Team, notification, or Inbox item.

### Key Entities *(include if feature involves data)*

- **Team**: Optional user-defined grouping of agents across one or more Hermes nodes.
- **AgentTeamMembership**: Link between an agent and a Team, retaining node identity.
- **ApprovalResponse**: User decision record that may approve, deny, modify, request info, escalate, or stop work.
- **ApprovalConstraint**: Explicit condition attached to an approval response.
- **ApprovalPolicy**: Persistent or proposed policy record created by Approve Forever.
- **TerminalSession**: A terminal session linked to node, agent, session, and assistance context where applicable.
- **TerminalIOEvent**: Terminal input/output event for backfill, audit, or replay.
- **AssistanceRequest**: Agent-originated or user-originated request for help.
- **AssistanceSession**: Active TUA context for collaborative resolution and handoff.
- **AssistanceMessage**: User or agent message inside a TUA session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can identify the correct agent, node, session, risk, and expiry on an approval card in under 15 seconds during review.
- **SC-002**: A user can complete Approve Once, Deny, More Info, Other, Open TUA Session, and Open TUI Session flows from one approval card without losing context.
- **SC-003**: 100% of Approve Forever decisions require a second confirmation and create or propose an approval policy record.
- **SC-004**: A user can complete the defined mobile Git workflow through TUI without needing a laptop.
- **SC-005**: A user can open a TUA session, ask for more information, modify the directive, and return control to the agent with a summary.
- **SC-006**: A user can browse at least 12 agents across at least 3 nodes and 3 Teams while preserving node/source context.
- **SC-007**: Every approval, TUI, and TUA action that changes agent execution creates an audit entry.
- **SC-008**: The five-tab navigation model can be explained from screen names and first-screen content without separate onboarding text.

## Assumptions

- TUI and TUA are product-level subsystems; implementation details can be phased.
- The first implementation can use planned schemas and placeholder screens before full terminal and assistance execution exist.
- Teams are an optional organization feature and do not replace node or agent identity.
- "Missions" refers to active or recent work contexts and can later map to Hermes sessions, tasks, or mission entities.
- Voice remains a first-class tab because future voice intervention is part of the product direction, even if voice implementation follows later.
- All mobile control surfaces continue to follow self-hosted-first, Tailscale-first, signed-device, and fail-closed approval constraints.

## Non-Goals

- Implementing production TUI, TUA, terminal PTY, or browser takeover code in this specification sprint.
- Replacing Hermes web portal administration workflows unrelated to mobile operation.
- Building a hosted relay or public SaaS control plane.
- Removing node identity or making Teams the source of truth.
- Allowing terminal paste, modified approvals, or policy creation to bypass gateway policy.
