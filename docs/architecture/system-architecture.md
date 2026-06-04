# System Architecture

## Purpose

Hermes Mobile Control Plane gives mobile users a private, auditable command surface for Hermes installs. It is self-hosted first, Tailscale first, and designed so a single Hermes node works on day one while many nodes, future relay access, and enterprise support remain possible.

This is an architecture foundation, not production implementation.

## Principles

- Self-hosted Hermes nodes do not require public exposure.
- Tailscale is the default connectivity path.
- The Hermes Control Gateway is the mobile-facing sidecar beside each Hermes install.
- Mobile approvals are safety-critical signed decisions, not ordinary chat messages.
- Push notifications are wake-up hints and never the durable source of truth.
- Audit logging is required for notification, approval, intervention, auth, and policy events.
- Hosted dependencies are avoided except where mobile platform push delivery requires APNs and FCM.

## High-Level Architecture

```mermaid
flowchart LR
  subgraph MobileDevice["Mobile Device"]
    IOS["iOS App"]
    Android["Android App"]
    KeyStore["Secure Storage\nKeychain / Keystore"]
  end

  subgraph Connectivity["Private Connectivity"]
    Tailnet["Tailscale Tailnet"]
    Local["Trusted Local Network"]
    Relay["Optional Future Relay"]
  end

  subgraph HermesHost["Hermes Host"]
    Gateway["Hermes Control Gateway"]
    Auth["Auth + Device Registry"]
    Approval["Approval Engine"]
    EventBus["Event Stream + Backfill"]
    Audit["Audit Log"]
    Push["Push Dispatcher"]
    VoiceCoord["Voice Coordinator"]
    Hermes["Hermes Agent Runtime"]
    Browser["Browser Subsystem"]
    Tools["MCP Tools / Shell / Files / Mail / Repo"]
    Voice["Hermes Voice Stack"]
  end

  subgraph External["External Services"]
    APNS["APNs"]
    FCM["FCM"]
  end

  IOS <--> KeyStore
  Android <--> KeyStore
  IOS <--> Tailnet
  Android <--> Tailnet
  IOS -. optional .-> Relay
  Android -. optional .-> Relay
  Tailnet <--> Gateway
  Local <--> Gateway
  Relay -. future .-> Gateway

  Gateway --> Auth
  Gateway --> Approval
  Gateway --> EventBus
  Gateway --> Audit
  Gateway --> Push
  Gateway --> VoiceCoord
  Gateway <--> Hermes
  Hermes <--> Browser
  Hermes <--> Tools
  Hermes <--> Voice
  VoiceCoord <--> Voice
  Push --> APNS
  Push --> FCM
```

## Deployment Topology

### Phase 1 Topology

One mobile app connects directly to one Hermes Control Gateway over Tailscale or trusted local network. The gateway runs on the same host or private network as Hermes and exposes pairing, REST state APIs, WebSocket events, approval APIs, and audit queries.

### Multi-Node Topology

Each Hermes node runs its own gateway. The mobile app stores a local inventory of registered gateways and connects to one or more gateways as needed. There is no required central coordinator.

### Optional Future Relay Topology

A relay may broker connectivity for users who cannot manage tailnets or local network access. The relay must not become required for self-hosted operation. It should forward encrypted sessions and avoid storing durable approval payloads where possible.

## Component Responsibility Matrix

| Component | Responsibilities | Does Not Own |
| --- | --- | --- |
| iOS App | Mobile UX, secure device key storage, pairing initiation, chat UI, approvals, live activity, notifications, voice UI, local node inventory | Server-side policy, durable audit storage, Hermes execution |
| Android App | Same as iOS with Android-specific notification, secure storage, and permission handling | Server-side policy, durable audit storage, Hermes execution |
| Hermes Control Gateway | Mobile API, device registry, auth, session token minting, event stream, approval queue, policy gate, audit log, push dispatch, agent inventory, voice coordination | Core Hermes reasoning, tool execution internals, mobile UI |
| Hermes Agent Runtime | Conversations, sessions, agent planning, tool requests, memory and skill use, session artifacts | Mobile auth, mobile audit retention, push provider integration |
| MCP Tools | Tool execution under Hermes policy and gateway approval constraints | Approval UI, notification routing, device trust |
| Browser Subsystem | Browser automation, screenshots, tab/session state, takeover hooks where supported | Mobile auth, push delivery |
| Voice Subsystem | Speech input/output integration, voice session media, voice mode state | Approval signing, device registration |
| Push Dispatcher | Secret filtering, notification rate limits, APNs/FCM dispatch, delivery attempt audit | Durable approval state, business logic execution |
| Event Stream + Backfill | WebSocket stream, event cursoring, replay after reconnect, live state fan-out | Long-term analytics warehouse |
| Audit Log | Immutable local record of auth, notification, approval, intervention, policy, and gateway events | User-facing notification delivery guarantee |
| Optional Relay | Future connectivity broker for non-tailnet users | Required self-hosted connectivity, approval source of truth |

## Trust Boundary Diagram

```mermaid
flowchart TB
  subgraph B1["Boundary 1: Mobile Device"]
    App["Mobile App"]
    DeviceKey["Device Private Key"]
    OSNotify["OS Notification Surface"]
  end

  subgraph B2["Boundary 2: Tailnet / Local Private Network"]
    Transport["Encrypted Private Transport"]
  end

  subgraph B3["Boundary 3: Hermes Host"]
    Gateway["Control Gateway"]
    Registry["Device Registry"]
    Approval["Approval Engine"]
    Audit["Audit Log"]
    Hermes["Hermes Agent"]
  end

  subgraph B4["Boundary 4: External Push Providers"]
    PushProvider["APNs / FCM"]
  end

  subgraph B5["Boundary 5: Optional Future Relay"]
    Relay["Hosted Relay"]
  end

  App <--> Transport
  Transport <--> Gateway
  Gateway <--> Registry
  Gateway <--> Approval
  Gateway --> Audit
  Gateway <--> Hermes
  Gateway --> PushProvider
  App -. future .-> Relay
  Relay -. future .-> Gateway
```

Trust boundary implications:

- Mobile device compromise can expose local node metadata and live session access until revoked.
- Tailscale identity helps authenticate network-level reachability but does not replace device registration.
- Gateway policy is authoritative for approvals and interventions.
- Push providers are untrusted for sensitive content. Payloads must be minimal and secret-free.
- Optional relay is untrusted for approval payload confidentiality unless end-to-end encryption is added.

## Core Data Flows

### Pairing Flow

```mermaid
sequenceDiagram
  participant U as User
  participant M as Mobile App
  participant G as Control Gateway
  participant R as Device Registry
  participant A as Audit Log

  U->>G: Opens local pairing session on trusted Hermes host
  G->>G: Creates short-lived pairing code / QR challenge
  U->>M: Scans code or enters pairing code
  M->>M: Generates device keypair in secure storage
  M->>G: Sends pairing challenge response + public key
  G->>R: Registers device identity and permissions
  G->>A: Records device_registered
  G->>M: Returns node identity and initial session token
```

### Chat Flow

```mermaid
sequenceDiagram
  participant M as Mobile App
  participant G as Control Gateway
  participant H as Hermes Agent
  participant E as Event Stream
  participant A as Audit Log

  M->>G: POST /chat/messages
  G->>A: audit chat_message_submitted
  G->>H: Relay message into session
  H-->>G: Streaming response events
  G-->>E: Publish message_delta / session_updated
  E-->>M: WebSocket event stream
```

### Live Activity Flow

```mermaid
sequenceDiagram
  participant H as Hermes Agent
  participant B as Browser / Tools
  participant G as Control Gateway
  participant E as Event Stream
  participant M as Mobile App

  H->>G: agent_status / plan_updated
  H->>B: Tool or browser action
  B-->>G: tool_run_updated / browser_state
  G->>E: Normalize event with cursor
  E-->>M: Push live event over WebSocket
  M->>G: GET /events/backfill?after=cursor on reconnect
```

### Approval And Push Flow

```mermaid
sequenceDiagram
  participant H as Hermes Agent
  participant G as Control Gateway
  participant P as Push Dispatcher
  participant N as APNs / FCM
  participant M as Mobile App
  participant A as Audit Log

  H->>G: approval_requested
  G->>G: Validate, redact, risk-score, persist pending approval
  G->>A: audit approval_requested
  G->>P: mobile_notify approval_required
  P->>P: Secret scan, rate limit, dedupe
  P->>N: Send minimal push payload
  N-->>M: Notification
  M->>G: GET approval detail
  M->>M: Sign approval decision with device key
  M->>G: POST approval decision
  G->>G: Verify signature, scope, expiry, policy
  G->>A: audit approval_decision
  G-->>H: Resume, deny, pause, or terminate
```

### Emergency Intervention Flow

```mermaid
sequenceDiagram
  participant M as Mobile App
  participant G as Control Gateway
  participant H as Hermes Agent
  participant A as Audit Log

  M->>M: User taps emergency stop
  M->>G: Signed intervention request
  G->>G: Verify device and permissions
  G->>H: Freeze agent / kill task / quarantine agent
  G->>A: audit emergency_intervention
  G-->>M: Confirm resulting state
```

### Voice Session Flow

```mermaid
sequenceDiagram
  participant M as Mobile App
  participant G as Voice Coordinator
  participant V as Hermes Voice Stack
  participant H as Hermes Agent
  participant A as Audit Log

  M->>G: Create voice session
  G->>A: audit voice_session_started
  M<->>G: Audio transport
  G<->>V: STT/TTS or voice mode bridge
  V<->>H: Voice instruction / response
  G-->>M: Agent audio and state updates
```

## Observability Requirements

- Every gateway request receives a request ID.
- Every event has `event_id`, `node_id`, `agent_id` when applicable, `session_id` when applicable, and monotonic `cursor`.
- Approval, intervention, notification, auth, policy, and voice events are audit logged.
- Gateway exposes health status for mobile and local diagnostics.
- Mobile app records non-sensitive client telemetry locally and may expose it for support export.

## Architectural Open Items

- Exact Hermes internal adapter APIs for agent, browser, shell, voice, and MCP event capture.
- Whether the gateway stores audit entries in Hermes' existing storage or its own local store.
- Whether future relay traffic is end-to-end encrypted at the application layer.
- Enterprise identity model beyond device-first local trust.
