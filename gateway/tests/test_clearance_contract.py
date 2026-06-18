from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

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
