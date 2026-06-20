"""Intervention queue: device-signed enqueue + hermes-local drain/ack.

The phone enqueues a pause/steer/stop command; the in-process plugin drains it
(loopback) and applies it at the agent's tool boundary, then acks it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def _enqueue(
    client: TestClient,
    paired: dict,
    *,
    itype: str = "pause",
    iid: str = "intv_test",
):
    return signed_request(
        client,
        "POST",
        "/v1/sessions/sess_mock/interventions",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
        json_body={
            "intervention_id": iid,
            "type": itype,
            "reason": f"test {itype}",
            "signed_payload": {"type": itype, "agent_id": "agent_mock"},
            "signature": "sig_test",
        },
    )


def _pending(client: TestClient) -> list[dict]:
    response = client.get(
        "/v1/runtime/interventions/pending?session_id=sess_mock&agent_id=agent_mock"
    )
    assert response.status_code == 200, response.text
    return response.json()["interventions"]


def test_intervention_enqueue_drain_ack(client: TestClient) -> None:
    paired = pair_device(client)

    enqueued = _enqueue(client, paired, itype="pause", iid="intv_1")
    assert enqueued.status_code == 200, enqueued.text
    assert enqueued.json()["resulting_state"] == "queued"

    items = _pending(client)
    assert any(
        i["intervention_id"] == "intv_1" and i["type"] == "pause" for i in items
    )

    ack = client.post(
        "/v1/runtime/interventions/intv_1/ack", json={"ack_result": "accepted"}
    )
    assert ack.status_code == 200, ack.text
    assert ack.json()["state"] == "acknowledged"

    # Acknowledged ⇒ no longer drained.
    assert all(i["intervention_id"] != "intv_1" for i in _pending(client))


def test_intervention_rejected_ack_state(client: TestClient) -> None:
    paired = pair_device(client)
    assert _enqueue(client, paired, itype="kill_task", iid="intv_2").status_code == 200
    ack = client.post(
        "/v1/runtime/interventions/intv_2/ack", json={"ack_result": "rejected"}
    )
    assert ack.status_code == 200
    assert ack.json()["state"] == "rejected"


def test_intervention_requires_intervene_capability(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve"])
    rejected = _enqueue(client, paired, iid="intv_3")
    assert rejected.status_code == 403


def test_ack_unknown_intervention_is_404(client: TestClient) -> None:
    response = client.post(
        "/v1/runtime/interventions/nope/ack", json={"ack_result": "accepted"}
    )
    assert response.status_code == 404
