# Approval Experience Review

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

## Purpose

The approval experience is the product's core differentiator. This review evaluates whether the current flow helps an operator safely understand, decide, modify, or intervene when Hermes wants to do something consequential.

## Overall Assessment

The approval system is strong because it separates a simple fail-closed state machine from richer operator responses. `pending`, `approved`, `denied`, `expired`, and `cancelled` remain easy to reason about, while `ApprovalResponse` handles modified instructions, more-info requests, constraints, and policy proposals.

The UI now exposes enough power to be useful, but the More menu is doing too much. It should become a structured decision surface, not a long catch-all menu.

## Action Review

| Action | Current Feel | Recommendation |
| --- | --- | --- |
| Approve Once | Elegant and safe. It maps cleanly to a signed single-action decision. | Keep as default positive action for high-risk requests. |
| Approve Session | Useful for repeated work in a single mission/session. | Keep, but show session boundary and expiry clearly. |
| Approve Agent | Powerful but riskier. | Keep for medium/high only with explicit agent and resource scope. |
| Deny | Clear and safe. | Keep as equally prominent to approve. |
| Modified Response | Valuable and differentiated. It lets the operator redirect without granting the original action. | Keep, but rename in UI to "Change Instruction" or "Modify Request" for clarity. |
| Needs Info | Useful when the operator wants Hermes to explain before proceeding. | Keep. Treat it as non-terminal and keep the approval pending. |
| Policy Proposal | Correctly avoids silent permanent policy creation. | Keep, but avoid "Approve Forever" as the primary label. Use "Propose Policy" with confirmation. |
| Browser Assistance | Good fit for web-task ambiguity. | Keep as an assistance path, not an approval decision. |
| TUA | Strong path when human judgment is needed. | Keep. It should be grouped under Assistance. |
| TUI | Powerful but dangerous. | Keep behind explicit TUI capability grants and risk labels. |

## Where The Experience Is Elegant

- The gateway fails closed on missing or invalid decisions.
- Device signatures make approval intent cryptographically meaningful.
- Modified responses prevent "approve with caveats" from being represented as a plain approval.
- Policy proposals keep permanent allow rules out of the automatic approval path.
- TUA/TUI launch from approval context keeps the operator anchored in the risky action.

## Where The Experience Is Excessive

- The More menu is long enough that users may miss critical actions or confuse decision actions with intervention actions.
- Approve For Agent and Approve Forever appear close to lower-risk choices; they need stronger visual separation.
- Emergency actions should not be visually equivalent to "More Info" or "Open TUA."
- The approval detail screen can require scrolling before reaching the actual decision controls.

## Recommended Approval Detail Layout

First screen:

- Risk badge and expiry countdown
- Agent, node, mission/session context
- Requested tool and summary
- Sticky bottom actions: Deny, Approve Once, More

Expanded context:

- Redacted payload
- Resource scope
- Constraints
- Audit/verification metadata

More sheet grouping:

- Decision: Approve For Session, Approve For Agent, Modify Request, Needs Info
- Assistance: Open TUA, Open TUI, Browser Assistance, More Info
- Policy: Propose Policy
- Emergency: Pause Agent, Stop Task, Stop Agent

## Risk Warning Improvements

High risk:

- Show resource scope before approval actions.
- Use confirmation for agent-scoped approval.
- Show whether constraints can be enforced.

Critical risk:

- Default primary action should be Deny or Review More, not Approve.
- Require explicit confirmation phrase or second tap.
- Hide permanent policy proposal unless policy creation is explicitly enabled for the risk category.

TUI:

- Show local PTY dev-only status when applicable.
- Show command and working directory constraints.
- Warn on paste with length and newline metadata.

Browser Assistance:

- Distinguish "view context" from "return control."
- Show that no live browser control is active until streaming/control is implemented.

Voice:

- Treat voice commands as drafts unless strong confirmation exists.
- Do not approve critical actions from voice without visible confirmation.

## Step Removal Opportunities

- Add one-tap "Needs Info" from Approval Detail for incomplete summaries.
- Launch TUA with approval context already attached.
- Let Modified Response reuse common constraint chips.
- Keep More sheet open after a failed signed request so the operator does not lose context.

## Decision

Keep the advanced approval system. Clean up the UX around it by grouping actions, making Deny and Approve Once persistently available, and treating policy creation and emergency controls as separate high-friction zones.
