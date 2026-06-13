# Product Assessment

Sprint lineage: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`, reframed by
`ACT-002`.

## 1. What Problem Does This Product Solve?

Agentic backends can act across tools, browsers, files, terminals, voice, and
multi-agent workflows. The missing piece is a trusted control tower that lets
the operator notice consequential work, understand what a backend is trying to
do, grant or deny clearance, and audit the outcome without exposing the backend
to the public internet.

Agentic Control Tower solves that by providing secure operator control for
self-hosted agentic backends:

- Monitor live backend and agent activity.
- Receive durable notices and urgent pushes.
- Grant, deny, modify, or escalate clearance requests.
- Open handoffs when human judgment is needed.
- Keep an audit trail of consequential actions.

## 2. Who Is The Primary User?

The primary user is a technical operator running one or more self-hosted
agentic backends in a homelab, laptop, workstation, VPS, or work VM.

They are comfortable with Tailscale, local gateways, terminals, and self-hosted
services. They want agents to be more autonomous, but they do not want autonomy
to become invisible or unsafe.

## 3. What Is The Killer Feature?

The killer feature is signed mobile clearance for consequential agent actions.

The operator can see what a backend wants to do, grant clearance once, deny it,
modify the instruction, request more information, or open a handoff. The phone
becomes the controller headset, not just another chat client.

## 4. What Differentiates It?

- Control-tower model: ACT authorizes, backends execute.
- Tailscale-first and self-hosted-first by default.
- No public exposure required for self-hosted operation.
- Device-key signatures for sensitive operator decisions.
- Fail-closed clearance engine.
- Durable notices and audit trail.
- Backend-neutral RuntimeAdapter seam.
- Hermes retained as adapter #1 instead of being treated as the platform
  boundary.

## 5. What Is This Product?

ACT is an agentic control tower.

It is not just a Hermes companion app, not just a mobile control plane, and not
yet a broad fleet operations platform. The product center is operator clearance
and audit for consequential backend actions.

## 6. Long-Term Naming Recommendation

Use:

- Full name: Agentic Control Tower
- Short name: ACT
- CLI binary: `tower`
- Package/distribution: `agentic-control-tower`
- Repository target: `AgenticControlTower`

Hermes-specific adapter code should continue to say Hermes where it is actually
describing Hermes.

## 7. Next Three Highest-Leverage Investments

1. Hardware-backed mobile signing and key lifecycle hardening.

   Prove key generation, storage, rotation, revocation, signed grant/deny, and
   gateway connection on native iOS and Android.

2. Allowlisted, secret-safe notification composition.

   Make notices useful without leaking secrets through OS notification surfaces.

3. Real Hermes runtime clearance.

   Wire the Hermes adapter deeply enough that a real Hermes action can request
   clearance, block, receive a signed mobile decision, and resume or stop.

## Final Assessment

Agentic Control Tower is worth continuing because powerful agentic backends need
a control tower, not only another chat surface. The next proof point is narrow
and concrete: one real Hermes action blocked on one real phone clearance.
