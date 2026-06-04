# Hermes Mobile Control Plane Framing

Hermes Mobile Control Plane is not just "Hermes chat on mobile." Hermes already supports web and browser control, memory, skills, subagents, voice mode, and multiple messaging platforms. The mobile product should wrap the existing agent surfaces while adding the missing safety and control layer.

The killer feature is:

> My agent is about to do something consequential. I can see exactly what it wants to do, approve it from my phone, modify the instruction, or stop it.

That is the missing piece for running Hermes in permissive or semi-autonomous mode safely.

## Core App Concept

A native iOS and Android app connects to one or more Hermes installs over Tailscale, local network, or an optional relay.

The app provides:

- Chat and web portal parity
- Multi-agent command center
- Approval control plane
- Live activity and intervention
- Future live voice mode

## Chat And Web Portal Parity

The mobile app should expose the Hermes workflows needed while away from the full web portal:

- Conversations
- Sessions
- Files and artifacts
- Skills and memory visibility
- Tool run history
- Browser or session viewer
- Agent status and logs

## Multi-Agent Command Center

The app should support multiple Hermes nodes and agents:

- Add multiple Hermes installs
- Label agents by environment, such as homelab, VPS, laptop, or work VM
- See active tasks per agent
- Start, pause, cancel, or redirect jobs
- Move a conversation or task between agents
- Keep node, agent, session, approval, notification, and audit context clearly separated

## Approval Control Plane

The approval layer is the first major differentiator.

Expected controls:

- Approve or deny risky tool calls
- Approve once
- Approve for this session
- Approve for this agent
- Approve permanent policy exception
- Always deny
- Pause agent
- Terminate task
- Emergency stop

Actions that should trigger escalation include:

- Shell execution
- Browser form submission
- File deletion
- Email sending
- Repository push
- Payment actions
- Credential access
- Network scanning
- Other destructive, irreversible, external, or sensitive operations

Pending approvals should support push notifications, direct deep links, and audit logging.

## Live Activity And Intervention

The mobile app should show what the agent is doing in real time:

- Current plan
- Current tool
- Current target
- Streaming terminal output where available
- Browser screenshot or live tab state where available
- Current blocking condition
- Recent tool history
- Agent status and logs

The user should be able to:

- Take over a browser or control session when available
- Inject an instruction mid-run
- Freeze an agent pending review
- Pause or cancel active work
- Trigger emergency stop

## Live Voice Mode

Voice should come after the core control plane is useful.

Suggested phases:

- Push-to-talk first
- Continuous conversation later
- Voice-to-agent and agent-to-voice
- Optional local speech-to-text and text-to-speech
- Optional server-side Hermes voice stack
- Voice approval with a required confirmation phrase
- Mobile walkie-talkie mode for agents

## Architecture Direction

Use the mobile app as a thin native client and add a small Hermes Control Gateway beside each Hermes install.

```text
Mobile App
  -> Tailscale / HTTPS / Relay
  -> Hermes Control Gateway
  -> Hermes Agent + tools + browser + shell + MCP
```

The gateway should expose:

- Authenticated event stream
- State and action API
- Approval queue API
- Agent registry
- Audit log
- Optional realtime stream for voice, browser, or screen state

## Security Model

Tailscale is the preferred default for self-hosted Hermes operators.

Connectivity posture:

- Default: Tailscale-only, no public exposure
- Acceptable: trusted local network for self-hosted use
- Good later option: HTTPS with device-bound tokens
- Later product option: hosted relay for non-technical users

For approvals, use signed action requests.

Example action request:

```yaml
tool: shell
command: rm -rf ./dist
risk: destructive-file-op
resource_scope: repo ./dist
expires: 60 seconds
```

Example mobile decision:

```yaml
decision: approve_once
signed_by: device_key
```

Every approval and denial should be logged.

## MVP Slices

Build in this order:

1. Read-only observer
   - Connect to one Hermes node
   - Show sessions, status, active task, and logs
2. Mobile chat
   - Send and receive messages
   - Stream responses
   - View artifacts
3. Approval queue
   - Push notification
   - Approve, deny, pause, or kill
   - Audit trail
4. Multi-agent registry
   - Add multiple Hermes installs
   - Switch between them
   - Global activity dashboard
5. Live intervention
   - Pause agent
   - Inject instruction
   - Cancel task
   - Browser and shell activity viewer
6. Voice
   - Push-to-talk first
   - Live voice later

## Suggested Stack For Planning

For fastest serious build:

- Frontend: React Native with Expo, or Flutter
- Gateway: FastAPI or Node/TypeScript
- Realtime: WebSockets
- Voice: WebRTC eventually, basic HTTP audio first
- Auth: device keypair, passkey unlock, and Tailscale identity
- Notifications: APNs and FCM
- Local secure storage: iOS Keychain and Android Keystore

These are planning preferences, not settled requirements.

## Strategic Fit

This project is aligned with Hermes, homelab operations, PromptFence, BrowserBridge, and broader control-plane work because it turns mobile into the safety, approval, and intervention surface for agentic systems.
