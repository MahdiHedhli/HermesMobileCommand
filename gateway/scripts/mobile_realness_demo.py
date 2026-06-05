from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_gateway.hermes_adapter import HermesToolAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local gateway for the mobile UI demo.")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--quiet-instructions",
        action="store_true",
        help="Only print IDs and URLs; omit app setup instructions.",
    )
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.port}/v1"
    with tempfile.TemporaryDirectory(prefix="hmcp-mobile-realness-") as temp_dir:
        process = _start_gateway(
            port=args.port,
            base_url=base_url,
            database_path=str(Path(temp_dir) / "gateway.sqlite3"),
        )
        try:
            _wait_for_gateway(base_url, process)
            adapter = HermesToolAdapter(gateway_base_url=base_url)
            approvals = [
                adapter.approval_requested(
                    requested_tool="shell",
                    risk_level="high",
                    summary="Run a redacted release verification command.",
                    payload_redacted={
                        "command": "python manage.py makemigrations --merge",
                        "cwd": "/repo",
                        "writes_files": True,
                    },
                    agent_id="agent_mock",
                    session_id="sess_release",
                    expires_in_seconds=900,
                    suggested_scopes=["once", "session"],
                    action_id="act_mobile_realness_release",
                ),
                adapter.approval_requested(
                    requested_tool="browser.submit",
                    risk_level="medium",
                    summary="Submit a vendor documentation feedback form.",
                    payload_redacted={
                        "url": "https://docs.vendor.example/feedback",
                        "form_fields": ["summary", "category"],
                    },
                    agent_id="agent_browser",
                    session_id="sess_browser",
                    expires_in_seconds=1200,
                    suggested_scopes=["once"],
                    action_id="act_mobile_realness_browser",
                ),
                adapter.approval_requested(
                    requested_tool="file.write",
                    risk_level="critical",
                    summary="Patch generated files after release verification.",
                    payload_redacted={
                        "paths": ["migrations/0008_merge.py"],
                        "writes_files": True,
                    },
                    agent_id="agent_mock",
                    session_id="sess_release",
                    expires_in_seconds=1500,
                    suggested_scopes=["once", "agent"],
                    action_id="act_mobile_realness_agent_scope",
                ),
            ]
            adapter.mobile_notify(
                title="Approval required",
                body="Repo Sentinel is waiting for a signed mobile decision.",
                urgency="high",
                category="approval_required",
                agent_id="agent_mock",
                session_id="sess_release",
                action_id=approvals[0]["action_id"],
            )
            instructions = []
            if not args.quiet_instructions:
                instructions = [
                    "Open the Flutter app.",
                    f"Set the gateway URL to {base_url} in Settings.",
                    "Start and complete pairing.",
                    "Open Home or Inbox; live status should show gateway events.",
                    "Open an approval and use More for once/session/agent actions.",
                ]
            print(
                json.dumps(
                    {
                        "gateway_base_url": base_url,
                        "approval_ids": [
                            approval["approval_id"] for approval in approvals
                        ],
                        "notification_created": True,
                        "instructions": instructions,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                flush=True,
            )
            _wait_until_stopped(process)
            return 0
        finally:
            _stop(process)


def _start_gateway(*, port: int, base_url: str, database_path: str) -> subprocess.Popen[str]:
    gateway_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    python_path = str(gateway_dir / "src")
    if env.get("PYTHONPATH"):
        python_path = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    env.update(
        {
            "PYTHONPATH": python_path,
            "HERMES_GATEWAY_DB": database_path,
            "HERMES_NODE_ID": "node_mobile_demo",
            "HERMES_NODE_DISPLAY_NAME": "Mobile Demo Hermes",
            "HERMES_NODE_FINGERPRINT": "mobile-demo-fingerprint",
            "HERMES_GATEWAY_BASE_URL": base_url,
        }
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "hermes_gateway.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(gateway_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for_gateway(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"gateway exited before becoming healthy:\n{output}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError:
            time.sleep(0.25)
            continue
        if payload["status"] == "healthy":
            return
    raise RuntimeError("gateway did not become healthy")


def _wait_until_stopped(process: subprocess.Popen[str]) -> None:
    try:
        while process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        return


def _stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
