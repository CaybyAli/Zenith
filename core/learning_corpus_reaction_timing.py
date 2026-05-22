from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReactionTimingResult:
    """Stable reaction-timing payload used by style_fingerprint.json."""

    applicable: bool
    events: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        if not self.applicable:
            return {"applicable": False}
        return {"applicable": True, "events": self.events or []}


_REACTION_TYPE_HINTS = {
    "vlog_main",
    "reaction",
    "reaction_main",
    "uncut_reaction",
}

_REACTION_TEXT_HINTS = {
    "reaction",
    "facecam",
    "face_cam",
    "webcam",
    "vlog",
    "antwort",
    "reagiert",
    "reaktion",
}


def extract_reaction_timing(
    *,
    video_type: str | None = None,
    meta: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
    scene_changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Passive reaction-timing scaffold.

    Active only for vlog_main or clearly reaction-like material. If not
    applicable, returns {"applicable": false} and never raises just because
    reaction material is absent.
    """

    if not is_reaction_applicable(video_type=video_type, meta=meta, transcript=transcript):
        return ReactionTimingResult(applicable=False).to_dict()

    events = build_reaction_events(
        transcript=transcript,
        scene_changes=scene_changes,
    )

    return ReactionTimingResult(applicable=True, events=events).to_dict()


def is_reaction_applicable(
    *,
    video_type: str | None = None,
    meta: dict[str, Any] | None = None,
    transcript: dict[str, Any] | None = None,
) -> bool:
    """Return whether reaction timing should run for this corpus item."""

    normalized_type = normalize_text(video_type or "")
    if normalized_type in _REACTION_TYPE_HINTS:
        return True

    meta = meta or {}
    meta_type = normalize_text(meta.get("type", ""))
    if meta_type in _REACTION_TYPE_HINTS:
        return True

    searchable_parts = [
        meta.get("video_id", ""),
        meta.get("game", ""),
        meta.get("youtube_url", ""),
        meta.get("title", ""),
        meta.get("description", ""),
        (transcript or {}).get("first_10s_text", ""),
    ]
    searchable_text = normalize_text(" ".join(str(part or "") for part in searchable_parts))

    return any(hint in searchable_text for hint in _REACTION_TEXT_HINTS)


def build_reaction_events(
    *,
    transcript: dict[str, Any] | None = None,
    scene_changes: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Build lightweight deterministic reaction placeholders.

    P5-1 keeps this passive. It does not inspect faces or execute edits.
    """

    first_text = normalize_text((transcript or {}).get("first_10s_text", ""))
    boundaries = (scene_changes or {}).get("boundaries_seconds", []) or []

    events: list[dict[str, Any]] = []

    if first_text:
        events.append(
            {
                "time_seconds": 0.0,
                "kind": "opening_reaction_candidate",
                "confidence": 0.5,
                "reason": "transcript_opening_present",
            }
        )

    for value in boundaries[:5]:
        time_seconds = _safe_seconds(value)
        if time_seconds <= 0:
            continue

        events.append(
            {
                "time_seconds": time_seconds,
                "kind": "scene_boundary_reaction_candidate",
                "confidence": 0.35,
                "reason": "scene_change_boundary",
            }
        )

    return events


def normalize_text(value: str) -> str:
    """Normalize text for deterministic matching."""

    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").lower().split())


def _safe_seconds(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return 0.0

    if converted < 0:
        return 0.0

    return round(converted, 3)
