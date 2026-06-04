from __future__ import annotations

from pathlib import Path

import yaml


def test_openapi_contract_includes_slice_paths() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text())
    paths = contract["paths"]
    assert "/pairing/start" in paths
    assert "/pairing/complete" in paths
    assert "/events/stream" in paths
    assert "/notifications/mobile_notify" in paths
    assert "/audit/events" in paths
