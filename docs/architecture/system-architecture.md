# System Architecture

## Purpose

Agentic Control Tower gives operators a private, auditable control tower for
agentic backends. It is self-hosted first and Tailscale first. Hermes is the
first concrete backend through the Hermes adapter, but the generic tower
boundary is `RuntimeAdapter`.

ACT does not execute backend actions. It grants or denies clearances, sequences
operator handoffs, tracks state, keeps the log, and enforces procedure. The
backends and agents are the aircraft; they do the flying.

## Principles

- Self-hosted backends do not require public exposure.
- Tailscale is the default connectivity path.
- The ACT Gateway is the mobile-facing control tower beside one or more
  backends.
- Mobile clearances are safety-critical signed decisions, not ordinary chat
  messages.
- Push notifications are wake-up hints and never the durable source of truth.
- Audit logging is required for notification, clearance, intervention, auth,
  handoff, and policy events.
- Hosted dependencies are avoided except where mobile platform push delivery
  requires APNs and FCM.
- Hermes remains adapter #1; Hermes-specific adapter code may still use Hermes
  terms where accurate.

## High-Level Architecture

```mermaid
flowchart LR
  subgraph MobileDevice["Operator Device"]
    IOS["iOS App"]
    Android["Android App"]
    KeyStore["Secure Storage\nKeychain / Keystore"]
  end

  subgraph Connectivity["Private Connectivity"]
    Tailnet["Tailscale Tailnet"]
    Local["Trusted Local Network"]
    Relay["Optional Future Relay"]
  end

  subgraph TowerHost["Tower / Backend Host"]
    Gateway["ACT Gateway"]
    Auth["Auth + Device Registry"]
    Clearance["Clearance Engine"]
    EventBus["Event Stream + Backfill"]
    Audit["Audit Log"]
    Push["Push Dispatcher"]
    Adapter["RuntimeAdapter"]
    HermesAdapter["Hermes Adapter #1"]
    Backend["Agentic Backend / Runtime"]
    Browser["Browser Subsystem"]
    Tools["Tools / Shell / Files / Mail / Repo"]
    Voice["Voice Stack"]
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
  Gateway --> Clearance
  Gateway --> EventBus
  Gateway --> Audit
  Gateway --> Push
  Gateway <--> Adapter
  Adapter <--> HermesAdapter
  HermesAdapter <--> Backend
  Backend <--> Browser
  Backend <--> Tools
  Backend <--> Voice
  Push --> APNS
  Push --> FCM
```

## Deployment Topology

### Phase 1 Topology

One mobile app connects directly to one ACT Gateway over Tailscale or trusted
local network. The gateway runs on the same host or private network as the
backend and exposes pairing, REST state APIs, WebSocket events, clearance APIs,
and audit queries. Hermes is the first backend through the Hermes adapter.

### Multi-Backend Topology

Each backend may run its own gateway. The mobile app stores a local inventory
of registered gateways and connects to one or more gateways as needed. There is
no required central coordinator.

### Optional Future Relay Topology

A relay may broker connectivity for users who cannot manage tailnets or local
network access. The relay must not become required for self-hosted operation.
It should forward encrypted sessions and avoid storing durable clearance
payloads where possible.

## Component Responsibility Matrix

| Component | Responsibilities | Does Not Own |
| --- | --- | --- |
| iOS App | Operator headset UX, secure device key storage, pairing initiation, clearances, live activity, notifications, voice UI, local node inventory | Server-side policy, durable audit storage, backend execution |
| Android App | Same as iOS with Android-specific notification, secure storage, and permission handling | Server-side policy, durable audit storage, backend execution |
| ACT Gateway | Mobile API, device registry, auth, event stream, clearance queue, policy gate, audit log, push dispatch, backend inventory | Core backend reasoning, action execution internals, mobile UI |
| RuntimeAdapter | Backend-specific translation into ACT work state, notices, clearances, and handoffs | Mobile auth, generic policy ownership, backend action execution |
| Hermes Adapter | First concrete adapter for Hermes runtime/tool policy and desktop integration | Generic tower protocol definition |
| Agentic Backend | Conversations, planning, action requests, memory and skill use, artifacts | Mobile auth, mobile audit retention, push provider integration |
| Tools | Execution under backend policy and ACT clearance constraints | Clearance UI, notification routing, device trust |
| Browser Subsystem | Browser automation, screenshots, tab/work state, takeover hooks where supported | Mobile auth, push delivery |
| Voice Subsystem | Speech input/output integration, voice media, voice mode state | Clearance signing, device registration |
| Push Dispatcher | Secret filtering, notification rate limits, APNs/FCM dispatch, delivery attempt audit | Durable clearance state, business logic execution |
| Event Stream + Backfill | WebSocket stream, event cursoring, replay after reconnect, live state fan-out | Long-term analytics warehouse |
| Audit Log | Immutable local record of auth, notification, clearance, intervention, policy, and gateway events | User-facing notification delivery guarantee |

## RuntimeAdapter Boundary

The generic RuntimeAdapter surface carries two primary traffic shapes:

- discrete-action clearance: one consequential action that must be granted,
  denied, modified, or cancelled
- handoff-with-return-of-control: the operator takes over or assists an
  in-progress work context, then returns a summary or message stream

The protocol uses backend-neutral terms such as `actor_ref`, `work_ref`,
`operation`, `clearance_ref`, and `handoff_ref`. Hermes-specific mission,
session, and tool semantics remain inside the Hermes adapter.

## Trust Boundary Diagram

```mermaid
flowchart TB
  subgraph B1["Boundary 1: Operator Device"]
    App["Mobile App"]
    DeviceKey["Device Private Key"]
    OSNotify["OS Notification Surface"]
  end

  subgraph B2["Boundary 2: Tailnet / Local Private Network"]
    Transport["Encrypted Private Transport"]
  end

  subgraph B3["Boundary 3: Tower / Backend Host"]
    Gateway["ACT Gateway"]
    Registry["Device Registry"]
    Clearance["Clearance Engine"]
    Audit["Audit Log"]
    Adapter["Runtime Adapter"]
    Backend["Agentic Backend"]
  end

  subgraph B4["Boundary 4: External Push Providers"]
    PushProvider["APNs / FCM"]
  end

  App <--> Transport
  Transport <--> Gateway
  Gateway <--> Registry
  Gateway <--> Clearance
  Gateway --> Audit
  Gateway <--> Adapter
  Adapter <--> Backend
  Gateway --> PushProvider
```

Trust boundary implications:

- Mobile device compromise can expose local backend metadata and live work
  access until revoked.
- Tailscale identity helps authenticate network-level reachability but does not
  replace device registration.
- Gateway policy is authoritative for clearances and interventions.
- Push providers are untrusted for sensitive content. Payloads must be minimal
  and secret-free.
- A backend may be honest, buggy, compromised, or intentionally rogue; adapters
  translate requests, but ACT remains the clearance authority.

## Core Data Flows

### Pairing Flow

```mermaid
sequenceDiagram
  participant U as Operator
  participant M as Mobile App
  participant G as ACT Gateway
  participant R as Device Registry
  participant A as Audit Log

  U->>G: Opens local pairing session on trusted host
  G->>G: Creates short-lived pairing code / QR challenge
  U->>M: Scans code or enters pairing code
  M->>M: Generates device keypair in secure storage
  M->>G: Sends pairing challenge response + public key
  G->>R: Registers device identity and permissions
  G->>A: Records device_registered
  G->>M: Returns node identity and initial token
```

### Clearance Flow

```mermaid
sequenceDiagram
  participant B as Backend
  participant R as RuntimeAdapter
  participant G as ACT Clearance Engine
  participant P as Push Dispatcher
  participant M as Mobile App
  participant A as Audit Log

  B->>R: Backend-specific consequential request
  R->>G: RuntimeClearanceRequest
  G->>G: Validate, redact, risk-score, persist pending clearance
  G->>A: audit clearance_requested
  G->>P: notice clearance_required
  P->>M: Minimal push hint
  M->>G: Fetch clearance detail
  M->>M: Sign grant/deny/modified decision with device key
  M->>G: Submit signed decision
  G->>G: Verify signature, scope, expiry, policy
  G->>A: audit clearance_decision
  G-->>R: Clearance result
  R-->>B: Backend-specific resume/deny/modify signal
```

### Handoff Flow

```mermaid
sequenceDiagram
  participant B as Backend
  participant R as RuntimeAdapter
  participant G as ACT Gateway
  participant M as Mobile App
  participant A as Audit Log

  B->>R: Need operator handoff
  R->>G: RuntimeHandoffRequest
  G->>A: audit handoff_requested
  M->>G: Open handoff
  M->>G: Send guidance / notes / return summary
  G->>A: audit return_control
  G-->>R: RuntimeHandoffResult
  R-->>B: Backend-specific return-of-control summary
```

## Observability Requirements

- Every gateway request receives a request ID.
- Every event has `event_id`, `node_id`, `agent_id` when applicable, work
  context when applicable, and monotonic `cursor`.
- Clearance, intervention, notification, auth, policy, and voice events are
  audit logged.
- Gateway exposes health status for mobile and local diagnostics.

## Architectural Open Items

- Exact Hermes bridge hook for real approval and clarify callbacks.
- Whether the gateway stores audit entries in backend storage or its own local
  store long-term.
- Whether future relay traffic is end-to-end encrypted at the application
  layer.
- Native mobile hardware-backed key behavior across iOS and Android.
