from __future__ import annotations

from dataclasses import dataclass

from .config import TRANSPORT_SPEED_KMH
from .models import UserRequest


INJECTION_MARKERS = (
    "ignore previous",
    "system prompt",
    "override instructions",
    "execute shell",
    "run command",
)


@dataclass(slots=True)
class SafetyResult:
    ok: bool
    reason: str = ""


class SafetyGuard:
    """Guards for unsafe input and side-effecting operations."""

    def validate_request(self, req: UserRequest) -> SafetyResult:
        full_text = " ".join(
            [req.city, req.style, " ".join(req.must_categories), " ".join(req.avoid_categories)]
        ).lower()
        for marker in INJECTION_MARKERS:
            if marker in full_text:
                return SafetyResult(False, f"prompt injection marker detected: {marker}")

        if req.duration_hours <= 0:
            return SafetyResult(False, "duration_hours must be > 0")
        if req.max_distance_km <= 0:
            return SafetyResult(False, "max_distance_km must be > 0")
        if req.duration_hours > 12:
            return SafetyResult(False, "duration_hours too high for walking route")
        if req.max_distance_km > 150:
            return SafetyResult(False, "max_distance_km too high for PoC limits")
        if req.transport_mode not in TRANSPORT_SPEED_KMH:
            return SafetyResult(False, f"unsupported transport_mode: {req.transport_mode}")

        return SafetyResult(True)

    def can_export_ics(self, confirmed: bool) -> SafetyResult:
        if not confirmed:
            return SafetyResult(False, "ICS export requires explicit confirmation")
        return SafetyResult(True)
