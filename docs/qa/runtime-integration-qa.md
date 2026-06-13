# Runtime Integration QA

Sprint: `HERMES-MCP-REAL-HERMES-CLIENT-008`

## Scope

This QA pass covers the gateway runtime client path, demo runtime agent, signed mobile-compatible actions, mission projection, and local E2E script. It does not cover native device builds, APNs, FCM, browser streaming, live audio, or real Hermes core patches.

## Approval Flow

| Scenario | Status | Evidence |
| --- | --- | --- |
| Create approval | Pass | Runtime client calls `POST /v1/runtime/approvals`; gateway tests and E2E create approvals. |
| Approve | Pass | E2E resolves `act_demo_approve` through signed `approve_session` response. |
| Deny | Pass | Existing approval lifecycle tests cover denial. |
| Modified response | Pass | E2E resolves `act_demo_modified` with alternate directive and constraint. |
| Timeout | Pass | `HermesRuntimeClient` wait helpers raise `RuntimeClientTimeout`. |
| Cancellation | Pass | Existing runtime endpoint supports approval cancel and test coverage remains. |

## TUA Flow

| Scenario | Status | Evidence |
| --- | --- | --- |
| Request | Pass | Demo agent calls `request_assistance`. |
| Message | Pass | E2E signed mobile path posts an assistance message. |
| Return control | Pass | E2E returns summary; runtime client receives it. |
| Close | Pass | Existing TUA lifecycle tests cover close. |

## Browser Assistance

| Scenario | Status | Evidence |
| --- | --- | --- |
| Request | Pass | Demo agent calls `request_browser_assistance`. |
| Return control | Pass | E2E posts note and return summary. |
| Close | Pass | Existing browser assistance tests cover close. |

## Voice

| Scenario | Status | Evidence |
| --- | --- | --- |
| Create | Pass | Demo agent calls `request_voice`. |
| Message | Pass | E2E posts signed text-backed voice message. |
| Close | Pass | E2E closes voice session and runtime client receives closed state. |

## Mission

| Scenario | Status | Evidence |
| --- | --- | --- |
| Create | Pass | Runtime context registration creates mission projection. |
| State transitions | Pass | Demo moves mission through running, waiting, user control, and completed states. |
| Completion | Pass | E2E verifies `mission_demo_runtime` reaches `completed`. |

## Capability Grants

| Scenario | Status | Evidence |
| --- | --- | --- |
| Allow | Pass | Runtime context capability metadata allows TUA, browser assistance, and voice in E2E. |
| Deny | Pass | Existing capability tests cover denied paths and audit records. |

## Not Tested

- Real external Hermes process lifecycle.
- Native iOS/Android secure storage behavior.
- Tailscale device identity integration.
- Callback-style runtime delivery.
- Production browser stream or audio transport.
