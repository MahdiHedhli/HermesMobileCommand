# Tasks: TUI, TUA, Teams, And Advanced Approval UX

**Input**: Design documents from `/specs/002-tui-tua-ux/`

**Prerequisites**: `spec.md`, `plan.md`, `docs/architecture/*`, ADRs, OpenAPI updates

**Tests**: Future implementation slices should add gateway contract tests, mobile widget tests, and E2E smoke paths as each subsystem becomes executable.

## Phase 1: Design Foundation

**Purpose**: Complete documentation and contract alignment.

- [x] T001 Create Spec Kit feature spec in `specs/002-tui-tua-ux/spec.md`
- [x] T002 Create Spec Kit checklist in `specs/002-tui-tua-ux/checklists/requirements.md`
- [x] T003 Create feature plan in `specs/002-tui-tua-ux/plan.md`
- [x] T004 Create task plan in `specs/002-tui-tua-ux/tasks.md`
- [x] T005 [P] Document TUI architecture in `docs/architecture/tui-architecture.md`
- [x] T006 [P] Document TUA architecture in `docs/architecture/tua-architecture.md`
- [x] T007 [P] Document advanced approval actions in `docs/architecture/advanced-approval-actions.md`
- [x] T008 [P] Document Teams grouping in `docs/architecture/teams-agent-grouping.md`
- [x] T009 Add ADRs for TUI, TUA, Agents/Teams terminology, and modified approvals
- [x] T010 Update OpenAPI planned endpoints and schemas in `docs/api/openapi.yaml`
- [x] T011 Update data model and mobile UX documentation

## Phase 2: Advanced Approval Implementation Slice

**Goal**: Support non-binary approval responses while staying fail-closed.

**Independent Test**: Hermes creates an approval; mobile submits modified instructions, constraints, More Info, Open TUA, Open TUI, and Approve Forever proposal; gateway audits each response and blocks unsupported policy expansion.

- [ ] T012 [P] [AdvancedApprovals] Add gateway models for `ApprovalResponse`, `ApprovalConstraint`, and `ApprovalPolicy`
- [ ] T013 [P] [AdvancedApprovals] Add OpenAPI contract tests for modified approval responses
- [ ] T014 [AdvancedApprovals] Implement signed approval response endpoint in `gateway/src/hermes_gateway/app.py`
- [ ] T015 [AdvancedApprovals] Persist response metadata and audit records in `gateway/src/hermes_gateway/store.py`
- [ ] T016 [AdvancedApprovals] Add mobile repository methods for More, Other, More Info, and Approve Forever flows
- [ ] T017 [AdvancedApprovals] Add E2E smoke path for modified approval response and policy proposal

## Phase 3: TUA Implementation Slice

**Goal**: Let agents request assistance and let users return control with a summary.

**Independent Test**: Hermes creates an assistance request; mobile opens a TUA session, exchanges messages, links an approval, returns control, and the gateway audits the handoff.

- [ ] T018 [P] [TUA] Add gateway models for `AssistanceRequest`, `AssistanceSession`, and `AssistanceMessage`
- [ ] T019 [P] [TUA] Add contract tests for TUA create/list/open/message/return-control endpoints
- [ ] T020 [TUA] Implement TUA endpoints in the gateway
- [ ] T021 [TUA] Emit event stream records for assistance requested, session opened, message created, and returned to agent
- [ ] T022 [TUA] Add mobile repository and screen skeleton for TUA sessions
- [ ] T023 [TUA] Add E2E smoke path for request-to-return-control

## Phase 4: TUI Implementation Slice

**Goal**: Add real mobile terminal sessions with attach/detach and safe paste controls.

**Independent Test**: A user attaches to a terminal session and completes the mobile Git workflow: inspect status, review diff, edit a file, run tests, commit, and push.

- [ ] T024 [P] [TUI] Add terminal session and terminal I/O models
- [ ] T025 [P] [TUI] Add contract tests for create/attach/detach/close/key/paste endpoints
- [ ] T026 [TUI] Implement WebSocket terminal attach and I/O stream gateway placeholder
- [ ] T027 [TUI] Add terminal permission and audit checks for key and paste events
- [ ] T028 [TUI] Add mobile terminal screen skeleton and key accessory bar
- [ ] T029 [TUI] Add smoke workflow for attach, send key, paste payload, detach, and close

## Phase 5: Teams And Navigation Slice

**Goal**: Make Agents the primary UI term and Teams an optional grouping layer.

**Independent Test**: A user creates Teams, assigns agents, browses Home/Agents/Missions/Voice/Inbox, and every action retains node/source context.

- [ ] T030 [P] [Teams] Add gateway models for `Team` and `AgentTeamMembership`
- [ ] T031 [P] [Teams] Add contract tests for list/create/assign/remove endpoints
- [ ] T032 [Teams] Implement Teams endpoints and event records
- [ ] T033 [Teams] Add mobile models/repositories for Teams
- [ ] T034 [Teams] Update mobile navigation to Home, Agents, Missions, Voice, and Inbox
- [ ] T035 [Teams] Add UI state tests for node/source context preservation

## Dependencies And Execution Order

- Phase 1 is complete in this design sprint.
- Phase 2 should come next because advanced approvals affect TUA and TUI escalation.
- Phase 3 can begin after the approval response shape is stable.
- Phase 4 can begin in parallel with Phase 3 if terminal security boundaries are explicit.
- Phase 5 can run after the data model names are stable, or in parallel as mobile UI-only scaffolding.
