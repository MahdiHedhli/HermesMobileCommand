from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .config import Settings
from .notification_composer import compose_notification
from .schemas import MobileNotifyRequest
from .security import canonical_json, content_hash, now_utc

CONTRACT_VERSION = "act.clearance.v1"
PROOF_ALGORITHM = "Ed25519"
PROOF_CANONICALIZATION = "ACT-CLEARANCE-PROOF-V1"
PROOF_BOUND_FIELDS = [
    "approval_id",
    "params_fingerprint",
    "short_code",
    "risk_family",
    "expires_at",
    "tower_id",
    "contract_version",
    "extensions_digest",
]


@dataclass(frozen=True)
class ClearanceProofMaterial:
    approval_id: str
    params_fingerprint: str
    short_code: str
    risk_family: str
    expires_at: str
    tower_id: str
    contract_version: str
    extensions_digest: str


def build_params_fingerprint(
    *,
    payload_redacted: dict[str, Any],
    extensions: dict[str, Any] | None,
) -> str:
    return content_hash(
        {
            "payload_redacted": payload_redacted,
            "extensions": extensions or {},
        }
    )


def extensions_digest(extensions: dict[str, Any] | None) -> str:
    return content_hash(extensions or {})


def build_short_code(approval_id: str, params_fingerprint: str) -> str:
    return hashlib.sha256(f"{approval_id}:{params_fingerprint}".encode("utf-8")).hexdigest()[
        :10
    ].upper()


def sanitize_operator_message(
    *,
    raw_message: str | None,
    settings: Settings,
    agent_id: str,
    session_id: str,
    risk_family: str,
    requested_tool: str,
) -> tuple[str | None, dict[str, Any]]:
    if raw_message is None:
        return None, {
            "composition_mode": "not_supplied",
            "unsafe_input_detected": False,
            "unsafe_reasons": [],
        }
    composed = compose_notification(
        MobileNotifyRequest(
            title="Clearance required",
            body=raw_message,
            urgency="normal",
            category="approval_required",
            agent_id=agent_id,
            session_id=session_id,
            backend_display_name=settings.node_display_name,
            subject_display_name=agent_id,
            risk_family=risk_family,
            operation_label=requested_tool,
        )
    )
    return composed.body, {
        "composition_mode": composed.mode,
        "template": composed.template,
        "unsafe_input_detected": composed.unsafe_input_detected,
        "unsafe_reasons": composed.unsafe_reasons,
        "safe_fields": composed.safe_fields,
    }


def build_clearance_contract_fields(
    *,
    settings: Settings,
    approval_id: str,
    payload_redacted: dict[str, Any],
    extensions: dict[str, Any] | None,
    risk_family: str,
    expires_at: str,
    requested_short_code: str | None = None,
) -> dict[str, Any]:
    params_fingerprint = build_params_fingerprint(
        payload_redacted=payload_redacted,
        extensions=extensions,
    )
    short_code = requested_short_code or build_short_code(approval_id, params_fingerprint)
    digest = extensions_digest(extensions)
    material = ClearanceProofMaterial(
        approval_id=approval_id,
        params_fingerprint=params_fingerprint,
        short_code=short_code,
        risk_family=risk_family,
        expires_at=expires_at,
        tower_id=settings.node_id,
        contract_version=CONTRACT_VERSION,
        extensions_digest=digest,
    )
    return {
        "params_fingerprint": params_fingerprint,
        "short_code": short_code,
        "tower_id": settings.node_id,
        "contract_version": CONTRACT_VERSION,
        "extensions": extensions or {},
        "extensions_digest": digest,
        "proof": create_clearance_proof(settings=settings, material=material),
    }


def proof_material_from_approval(approval: dict[str, Any]) -> ClearanceProofMaterial:
    return ClearanceProofMaterial(
        approval_id=approval["approval_id"],
        params_fingerprint=approval["params_fingerprint"],
        short_code=approval["short_code"],
        risk_family=approval["risk_family"],
        expires_at=approval["expires_at"],
        tower_id=approval["tower_id"],
        contract_version=approval["contract_version"],
        extensions_digest=approval["extensions_digest"],
    )


def canonical_proof_string(material: ClearanceProofMaterial) -> str:
    return "\n".join(
        [
            PROOF_CANONICALIZATION,
            material.approval_id,
            material.params_fingerprint,
            material.short_code,
            material.risk_family,
            material.expires_at,
            material.tower_id,
            material.contract_version,
            material.extensions_digest,
        ]
    )


def create_clearance_proof(
    *,
    settings: Settings,
    material: ClearanceProofMaterial,
) -> dict[str, Any]:
    private_key = _tower_private_key(settings)
    signature = private_key.sign(canonical_proof_string(material).encode("utf-8"))
    return {
        "algorithm": PROOF_ALGORITHM,
        "canonicalization": PROOF_CANONICALIZATION,
        "key_id": f"tower:{material.tower_id}",
        "signed_at": now_utc().isoformat().replace("+00:00", "Z"),
        "fields": PROOF_BOUND_FIELDS,
        "extensions_digest": material.extensions_digest,
        "signature": _b64url(signature),
    }


def verify_clearance_proof(
    *,
    public_key_b64: str,
    material: ClearanceProofMaterial,
    proof: dict[str, Any],
) -> bool:
    if proof.get("algorithm") != PROOF_ALGORITHM:
        return False
    if proof.get("canonicalization") != PROOF_CANONICALIZATION:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_b64decode(public_key_b64))
        public_key.verify(
            _b64decode(str(proof.get("signature", ""))),
            canonical_proof_string(material).encode("utf-8"),
        )
    except (ValueError, InvalidSignature):
        return False
    return True


def tower_public_key_b64(settings: Settings) -> str:
    return _b64url(_tower_private_key(settings).public_key().public_bytes_raw())


def canonical_extensions(value: dict[str, Any] | None) -> str:
    return canonical_json(value or {})


def _tower_private_key(settings: Settings) -> Ed25519PrivateKey:
    seed = hashlib.sha256(f"act-tower-proof:{settings.node_fingerprint}".encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
