# Product Assessment

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

## 1. What Problem Does This Product Solve?

Hermes can act across tools, browsers, files, terminals, voice, and multi-agent workflows. The missing piece is a trusted mobile control layer that lets the owner notice consequential work, understand what Hermes is trying to do, and intervene without exposing the self-hosted install to the public internet.

Hermes Mobile Control Plane solves that by providing secure mobile operations for self-hosted Hermes nodes:

- Monitor live agent activity.
- Receive durable notifications and urgent pushes.
- Approve, deny, modify, or escalate risky actions.
- Open assistance, terminal, browser, or voice sessions when human judgment is needed.
- Manage multiple agents and nodes from a single operator surface.

## 2. Who Is The Primary User?

The primary user is a technical operator running Hermes in a homelab, laptop, workstation, VPS, or work VM environment.

They are comfortable with Tailscale, local gateways, terminals, and self-hosted services. They want Hermes to be more autonomous, but they do not want autonomy to become invisible or unsafe.

Secondary future users:

- Power users supervising personal agent fleets.
- Small teams running shared Hermes nodes.
- Enterprise operators who need auditability, scoped device trust, and policy review.

## 3. What Is The Killer Feature?

The killer feature is signed mobile intervention for consequential agent actions.

The operator can see what Hermes wants to do, approve it once, deny it, modify the instruction, request more information, open an assistance session, open a terminal, or propose a policy. The phone becomes the safety and intervention console, not just another chat client.

## 4. What Differentiates It?

Differentiators:

- Tailscale-first and self-hosted-first by default.
- No public exposure required for self-hosted Hermes installs.
- Device-key signatures for sensitive mobile actions.
- Fail-closed approval engine.
- Durable notifications and audit trail.
- Multi-agent control model rather than a single chat window.
- Operator sessions that span terminal, assistance, browser, and voice.
- Designed for permissive or semi-autonomous agent operation where safety matters.

## 5. What Is This Product?

It is primarily a mobile control plane.

It is also becoming an agent operations platform, but the center of gravity should remain mobile operator intervention until beta. Calling it only a companion app undersells the security, approval, audit, and multi-agent control-plane work.

Current identity:

- Hermes Mobile Control Plane

Long-term identity:

- Hermes Command, if the product becomes broader than mobile.
- Hermes Operator, if the product centers on human-agent supervision.
- Hermes Mobile Control Plane should remain the project name through beta because it is precise and aligned with the current scope.

## 6. Long-Term Naming Recommendation

Keep `Hermes Mobile Control Plane` for the repository, docs, and beta planning.

Use `Hermes Command` as the short product label in the app if the UI needs a tighter title. The current app already presents "Hermes Command," which fits the operator-console tone without forcing a repository rename.

Avoid:

- Hermes Chat Mobile
- Hermes Companion
- Hermes Wingman fork naming

Those names pull the product toward chat or GUI replacement, while the product has become an intervention and operations layer.

## 7. Next Three Highest-Leverage Investments

1. Native signed approval flow.

   Prove pairing, secure key storage, signed approve/deny, and gateway connection on iOS and Android. This turns the product from a web-demo control plane into a real mobile app.

2. OperatorSession and CapabilityGrant consolidation.

   Make TUI, TUA, browser assistance, and voice legible as intervention modes while preserving mode-specific safety checks. Promote grants into explicit audited policy.

3. Real Hermes runtime handoff.

   Wire the gateway deeply enough that Hermes can request approvals, block, receive decisions, use returned assistance summaries, and reflect real mission state in the mobile app.

## Final Assessment

Hermes Mobile Control Plane is worth continuing as a real project. The product has a clear reason to exist: safe mobile supervision for self-hosted autonomous agents. Its strongest future is not "chat with Hermes from a phone." Its strongest future is "operate Hermes safely when it is powerful enough to need supervision."
