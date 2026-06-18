from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request
from hermes_gateway.clearance_contract import (
    ClearanceProofMaterial,
    extensions_digest,
    proof_material_from_approval,
    tower_public_key_b64,
    verify_clearance_proof,
)


def test_clearance_proof_test_vector_verifies_and_bound_mutations_fail() -> None:
    vector_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "clearance"
        / "test-vector.json"
    )
    vector = json.loads(vector_path.read_text())
    material = ClearanceProofMaterial(**vector["material"])

    assert verify_clearance_proof(
        public_key_b64=vector["tower_public_key"],
        material=material,
        proof=vector["proof"],
    )

    mutations = {
        "params_fingerprint": "0" * 64,
        "short_code": "CHANGED123",
        "risk_family": "read_only",
        "expires_at": "2026-06-18T13:00:00Z",
        "extensions_digest": "1" * 64,
        "tower_id": "tower_other",
    }
    for field, value in mutations.items():
        assert not verify_clearance_proof(
            public_key_b64=vector["tower_public_key"],
            material=replace(material, **{field: value}),
            proof=vector["proof"],
        ), field


def test_created_clearance_proof_verifies(client: TestClient) -> None:
    response = client.post(
        "/v1/runtime/approvals",
        json={
            "requested_tool": "shell",
            "risk_level": "high",
            "risk_family": "external_effect",
            "summary": "Run a redacted runtime command.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_runtime",
            "session_id": "sess_runtime",
            "expires_in_seconds": 300,
            "extensions": {
                "agentickvm": {
                    "target": "vm-alpha",
                    "provider": "local",
                    "capability": "power-cycle",
                    "risk_summary": "External effect on a VM",
                }
            },
        },
    )

    assert response.status_code == 201
    approval = response.json()
    material = proof_material_from_approval(approval)
    assert material.extensions_digest == extensions_digest(approval["extensions"])
    assert verify_clearance_proof(
        public_key_b64=tower_public_key_b64(client.app.state.settings),
        material=material,
        proof=approval["proof"],
    )


def test_poll_and_status_shapes_carry_canonical_clearance_fields(
    client: TestClient,
) -> None:
    approval = _runtime_approval(
        client,
        operator_message="Please review the redacted request.",
        audit_correlation_id="akvm-audit-123",
    )

    runtime_result = client.get(f"/v1/runtime/approvals/{approval['approval_id']}/result")
    assert runtime_result.status_code == 200
    result_body = runtime_result.json()

    hermes_status = client.post(
        "/v1/hermes/tools/approval_status",
        json={"approval_id": approval["approval_id"]},
    )
    assert hermes_status.status_code == 200
    status_body = hermes_status.json()

    for body in (result_body, status_body):
        assert body["risk_family"] == approval["risk_family"]
        assert body["expires_at"] == approval["expires_at"]
        assert body["params_fingerprint"] == approval["params_fingerprint"]
        assert body["short_code"] == approval["short_code"]
        assert body["operator_message"] == approval["operator_message"]
        assert body["audit_correlation_id"] == "akvm-audit-123"
        assert body["tower_id"] == "node_test"
        assert body["contract_version"] == "act.clearance.v1"
        assert body["proof"]["signature"] == approval["proof"]["signature"]


def test_operator_message_secret_is_sanitized_and_raw_absent_from_audit(
    client: TestClient,
) -> None:
    paired = pair_device(client)
    raw_secret = "Submit reset form with token=abc123SECRETvalue"
    approval = _runtime_approval(client, operator_message=raw_secret)

    assert approval["operator_message"] != raw_secret
    assert "abc123" not in approval["operator_message"]

    result = client.get(f"/v1/runtime/approvals/{approval['approval_id']}/result")
    assert result.status_code == 200
    result_text = result.text
    assert raw_secret not in result_text
    assert "abc123" not in result_text

    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=approval_requested",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    audit_text = audit.text
    assert raw_secret not in audit_text
    assert "abc123" not in audit_text
    assert "token_like_text_detected" in audit_text


def _runtime_approval(
    client: TestClient,
    *,
    operator_message: str | None = None,
    audit_correlation_id: str | None = None,
) -> dict:
    payload = {
        "requested_tool": "shell",
        "risk_level": "high",
        "risk_family": "external_effect",
        "summary": "Run a redacted runtime command.",
        "payload_redacted": {"command": "redacted"},
        "agent_id": "agent_runtime",
        "session_id": "sess_runtime",
        "expires_in_seconds": 300,
        "extensions": {
            "agentickvm": {
                "target": "vm-alpha",
                "provider": "local",
                "capability": "power-cycle",
                "risk_summary": "External effect on a VM",
            }
        },
    }
    if operator_message is not None:
        payload["operator_message"] = operator_message
    if audit_correlation_id is not None:
        payload["audit_correlation_id"] = audit_correlation_id
    response = client.post("/v1/runtime/approvals", json=payload)
    assert response.status_code == 201
    return response.json()
