"""Risk-class → required-channel policy + authority provenance mapping.

BrowserBridge seam (additive). Binds a per-surface browser risk class to the
operator channel that must make the decision, so "high-risk form-submit →
mobile-mandatory" is expressible as policy rather than convention. When an
approval carries no ``risk_vector`` no channel is required and existing behavior
is unchanged; once a vector demands a channel the decision is fail-closed.
"""

from __future__ import annotations

from typing import Any

# decision channel → typed authority-provenance class.
_CHANNEL_AUTHORITY = {
    "mobile_signed": "human_mobile",
    "local_terminal": "human_local",
}

# device platform → decision channel. Mobile platforms decide over the
# Secure-Enclave (mobile_signed) channel; desktop/terminal over local_terminal.
_MOBILE_PLATFORMS = {"ios", "ipados", "android"}
_LOCAL_PLATFORMS = {"macos", "linux", "windows", "local", "terminal", "cli"}


def channel_for_device(device: dict[str, Any] | None) -> str | None:
    """Resolve a device's decision channel. Prefers an explicit
    ``clearance_channel`` (bridge-era devices) and falls back to the device
    ``platform`` so the policy works on the base contract too."""
    if not device:
        return None
    channel = device.get("clearance_channel")
    if channel:
        return channel
    platform = (device.get("platform") or "").lower()
    if platform in _MOBILE_PLATFORMS:
        return "mobile_signed"
    if platform in _LOCAL_PLATFORMS:
        return "local_terminal"
    return None

# Risk-class values considered high enough to mandate the mobile channel.
HIGH_RISK_CLASS_VALUES = {"high", "critical"}
MOBILE_MANDATORY_CHANNELS = ("mobile_signed",)
_RISK_CLASS_KEYS = ("submit_risk_class", "click_risk_class", "field_class")


def authority_from_channel(channel: str | None) -> str:
    """Map a device's clearance channel to a typed authority class.

    Unknown/None channels resolve to ``test_operator`` (e.g. dev/test devices
    not bound to a human-operator channel)."""
    return _CHANNEL_AUTHORITY.get(channel or "", "test_operator")


def required_channels_for_risk_vector(
    risk_vector: dict[str, Any] | None,
) -> tuple[str, ...] | None:
    """Channels permitted to decide an approval carrying this risk vector, or
    ``None`` when the vector imposes no channel requirement."""
    if not risk_vector:
        return None
    for key in _RISK_CLASS_KEYS:
        value = risk_vector.get(key)
        if isinstance(value, str) and value.lower() in HIGH_RISK_CLASS_VALUES:
            return MOBILE_MANDATORY_CHANNELS
    return None


def channel_satisfies(
    channel: str | None, required: tuple[str, ...] | None
) -> bool:
    """True if ``channel`` is allowed to decide given the requirement (or there
    is no requirement)."""
    if not required:
        return True
    return (channel or "") in required
