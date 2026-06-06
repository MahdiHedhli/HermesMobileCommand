# UX Consistency Review

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

## Scope

Reviewed screens:

- Home
- Agents
- Agent Detail
- Inbox
- Approvals
- TUA
- TUI
- Browser Assistance
- Voice
- Missions
- Settings

## Overall Assessment

The app now reads as a mobile operator console, not a chat app. The dark utilitarian style, bottom tab model, agent-first navigation, and approval detail surfaces are coherent. The strongest pattern is contextual intervention: an operator sees a risky or blocked action, opens the relevant session type, acts, then returns control.

The main UX debt is that intervention modes have grown faster than the information architecture. TUA, TUI, Browser Assistance, and Voice feel like separate destinations, but the operator mental model is "help this agent with this mission." That argues for a shared Operator Session layer in Home, Inbox, Missions, and Agent Detail.

## Navigation Consistency

What works:

- Bottom navigation keeps the main operating modes stable: Home, Agents, Missions, Voice, Inbox.
- Settings access is consistently available from top app bars.
- Approval detail can launch TUA and TUI with context, which matches the intervention-first product direction.
- Agent list grouping by team is useful without hiding node/source identity.

Issues:

- Browser Assistance is useful but not yet as discoverable as TUA/TUI.
- The More menu carries too many unrelated concepts in one vertical list.
- Approval primary actions can fall below the first screen on mobile.
- TUA, TUI, Browser Assistance, and Voice use different status language for similar lifecycle concepts.
- iPad usage is not validated; current screens are mostly single-column mobile layouts.

Recommendations:

- Keep the five-tab model.
- Add a shared "Sessions" or "Interventions" section inside Agent Detail and Mission Detail.
- Use one lifecycle vocabulary for operator intervention: requested, active, user controlling, returned, closed.
- On tablet, use split views for list plus detail screens: Agents, Inbox, Approvals, and Missions.

## Naming Consistency

Preferred terms:

- Product: Hermes Mobile Control Plane
- Operator-facing actor: Agent
- Work context: Mission
- Human intervention container: Operator Session
- Terminal mode: TUI
- Assistance mode: TUA
- Browser mode: Browser Assistance
- Voice mode: Voice Session
- Attention item: Notification

Terms to avoid or reduce:

- "Node" as primary UI text. Keep it visible as infrastructure context, but users operate agents.
- "Session" without qualifier. It can mean Hermes session, TUI session, TUA session, voice session, or operator session.
- "Approve Forever" as a plain approval. It should always be framed as "Policy Proposal" or "Propose Always Allow."

## Screen Findings

| Screen | Strengths | Friction | Recommendation |
| --- | --- | --- | --- |
| Home | Dense and operator-focused; status cards make fleet health visible. | Mock/live state distinction is visible but should become less prominent in production. | Keep as command overview. Add live event badges and a compact active operator sessions strip. |
| Agents | Search, filters, and team grouping fit the product. | Team is useful but may look more authoritative than it is. | Label grouping as organizational. Keep node/source visible on every agent card. |
| Agent Detail | Good place for capabilities, notifications, approvals. | Needs stronger mission and operator-session history. | Make Agent Detail the local command page for one agent. |
| Inbox | Correct unified attention model. | Notifications, approvals, and assistance requests need clearer type colors/icons. | Keep unified, but add type filters and unread triage shortcuts. |
| Approval Detail | Rich context and real signed actions. | Primary decision actions are not always first-screen accessible. | Add sticky Approve/Deny/More action rail or bottom bar. |
| More Menu | Contains the right advanced decisions. | Too long and mixes decisions, assistance, and emergency controls. | Group into Decision, Assistance, and Emergency sections. |
| TUA | Good agent-message timeline and return-control flow. | Needs clearer state transition from assisting to returned. | Show a persistent state banner and mission context. |
| TUI | Strong terminal feel; accessory bar is the right differentiator. | Requires clearer risk labeling when local PTY is enabled. | Keep accessory bar, add session state and dev-only warning when live PTY is active. |
| Browser Assistance | Good thin model for notes and return control. | Feels sparse because no screenshot/stream exists yet. | Present as an assistance log until streaming exists. |
| Voice | Useful text-backed MVP. | Voice availability and live audio future state should not dominate the screen. | Keep as push-to-talk style entry with text fallback. |
| Missions | Correct work-context destination. | Backend Mission model is not yet canonical. | Make Missions the cross-agent work ledger once durable data lands. |
| Settings | Gateway config and pairing belong here. | Pairing status, storage mode, and native warnings need stronger visual hierarchy. | Add an "Identity and Gateway" section with device trust state. |

## High-Friction Workflows

- Reviewing a high-risk approval then choosing an advanced response takes several scrolls/taps.
- Starting from an agent and finding all active interventions for that agent is not yet obvious.
- Browser Assistance launch is not prominent enough from approval context.
- Resetting or validating pairing is present, but not yet productized as a device lifecycle flow.
- Native target readiness is documented, but the app is still validated primarily on Chrome.

## iPad Usability

Current status: Needs Work.

Recommended iPad layouts:

- Agents: grouped list on left, Agent Detail on right.
- Inbox: attention list on left, Approval/Notification detail on right.
- TUI: terminal full-height with accessory controls docked at bottom.
- TUA/Browser Assistance: conversation or event log on left, context/actions on right.
- Settings: section list on left, selected settings pane on right.

## Next UX Cleanup Priorities

1. Add sticky approval decision controls.
2. Group More menu actions by intent.
3. Add an Operator Sessions rail to Home, Agent Detail, and Mission Detail.
4. Standardize lifecycle labels across TUA, TUI, Browser Assistance, and Voice.
5. Add tablet split layouts before TestFlight-quality builds.
