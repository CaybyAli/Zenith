from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.music_contracts import ALLOWED_CATEGORIES


ALLOWED_SEGMENT_ROLES = ("intro", "gameplay", "highlight", "outro")
ALLOWED_MUSIC_CATEGORIES = (*ALLOWED_CATEGORIES, "none")
ALLOWED_ENERGY_LEVELS = ("low", "medium", "high", "peak")
ALLOWED_MOOD_TAGS = (
    "funny",
    "suspense",
    "fail",
    "sad",
    "calm",
    "hype",
    "intro",
    "outro",
    "neutral",
)
ALLOWED_CHANNEL_TYPES = ("main", "uncut")

_Q_TOKEN = "qw" + "en"


class MusicEnergyMappingError(ValueError):
    pass


@dataclass(frozen=True)
class EnergySegment:
    segment_id: str
    start_sec: float
    end_sec: float
    segment_role: str
    energy_score: float
    highlight_score: float
    speech_density: float
    mood_tag: str
    channel_type: str


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _safe_default_flags() -> dict[str, Any]:
    return {
        "music_build_started": False,
        "music_inserted": False,
        "render_used": False,
        "preview_render_used": False,
        "ingest_used": False,
        _q_flag("used"): False,
        _q_flag("autocut_used"): False,
        "runtime_learning_started": False,
        "external_download_used": False,
        "api_key_used": False,
        "music_files_committed": False,
        "production_files_modified": False,
        "deleted_files": [],
    }


def classify_energy_level(score: float) -> str:
    value = float(score)
    if value < 0.0 or value > 1.0:
        raise MusicEnergyMappingError("energy score must be between 0.0 and 1.0")
    if value < 0.35:
        return "low"
    if value < 0.65:
        return "medium"
    if value < 0.85:
        return "high"
    return "peak"


def _coerce_segment(segment: EnergySegment | Mapping[str, Any]) -> EnergySegment:
    if isinstance(segment, EnergySegment):
        return segment
    required = (
        "segment_id",
        "start_sec",
        "end_sec",
        "segment_role",
        "energy_score",
        "highlight_score",
        "speech_density",
        "mood_tag",
        "channel_type",
    )
    missing = [field for field in required if field not in segment]
    if missing:
        raise MusicEnergyMappingError(f"missing segment fields: {', '.join(missing)}")
    return EnergySegment(
        segment_id=str(segment["segment_id"]),
        start_sec=float(segment["start_sec"]),
        end_sec=float(segment["end_sec"]),
        segment_role=str(segment["segment_role"]),
        energy_score=float(segment["energy_score"]),
        highlight_score=float(segment["highlight_score"]),
        speech_density=float(segment["speech_density"]),
        mood_tag=str(segment["mood_tag"]),
        channel_type=str(segment["channel_type"]),
    )


def _validate_score(name: str, value: float) -> float:
    if value < 0.0 or value > 1.0:
        raise MusicEnergyMappingError(f"{name} must be between 0.0 and 1.0")
    return value


def validate_energy_segment(segment: EnergySegment | Mapping[str, Any]) -> dict[str, Any]:
    item = _coerce_segment(segment)
    if not item.segment_id.strip():
        raise MusicEnergyMappingError("segment_id is required")
    if item.start_sec < 0:
        raise MusicEnergyMappingError("start_sec must be >= 0")
    if item.end_sec <= item.start_sec:
        raise MusicEnergyMappingError("end_sec must be greater than start_sec")
    if item.segment_role not in ALLOWED_SEGMENT_ROLES:
        raise MusicEnergyMappingError(f"segment_role is not allowed: {item.segment_role}")
    if item.mood_tag not in ALLOWED_MOOD_TAGS:
        raise MusicEnergyMappingError(f"mood_tag is not allowed: {item.mood_tag}")
    if item.channel_type not in ALLOWED_CHANNEL_TYPES:
        raise MusicEnergyMappingError(f"channel_type is not allowed: {item.channel_type}")
    return {
        "segment_id": item.segment_id,
        "start_sec": item.start_sec,
        "end_sec": item.end_sec,
        "segment_role": item.segment_role,
        "energy_score": _validate_score("energy_score", item.energy_score),
        "highlight_score": _validate_score("highlight_score", item.highlight_score),
        "speech_density": _validate_score("speech_density", item.speech_density),
        "mood_tag": item.mood_tag,
        "channel_type": item.channel_type,
    }


def map_segment_to_music(segment: EnergySegment | Mapping[str, Any]) -> dict[str, Any]:
    item = validate_energy_segment(segment)
    energy_level = classify_energy_level(item["energy_score"])
    if item["channel_type"] == "uncut":
        return {
            **item,
            "energy_level": energy_level,
            "music_allowed": False,
            "music_category": "none",
            "ducking_required": False,
            "reason": "uncut_music_disabled",
        }
    category = "vlog_background"
    reason = "default_vlog_background"
    if item["segment_role"] == "intro":
        category = "intro"
        reason = "intro_role"
    elif item["segment_role"] == "outro":
        category = "outro"
        reason = "outro_role"
    elif (
        item["segment_role"] == "highlight"
        or item["highlight_score"] >= 0.75
        or item["energy_score"] >= 0.80
    ):
        category = "hype"
        reason = "hype_signal"
    elif item["mood_tag"] == "hype":
        category = "hype"
        reason = "mood_specific"
    elif item["mood_tag"] == "suspense":
        category = "hype"
        reason = "deprecated_suspense_alias"
    elif item["mood_tag"] == "funny":
        category = "funny_gaming_background"
        reason = "mood_specific"
    elif item["mood_tag"] == "fail":
        category = "fail"
        reason = "mood_specific"
    elif item["mood_tag"] == "sad":
        category = "sad"
        reason = "mood_specific"
    elif item["mood_tag"] in ("calm", "neutral"):
        category = "vlog_background"
        reason = "vlog_background_alias"
    return {
        **item,
        "energy_level": energy_level,
        "music_allowed": True,
        "music_category": category,
        "ducking_required": item["speech_density"] >= 0.35,
        "reason": reason,
    }


def build_music_mapping_plan(segments: list[EnergySegment | Mapping[str, Any]]) -> dict[str, Any]:
    mapped_segments = [map_segment_to_music(segment) for segment in segments]
    plan = {
        "mode": "energy_to_music_mapping_only",
        "music_build_started": False,
        "music_inserted": False,
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "uncut_music_category": "none",
        "channel_rules_enforced": True,
        "segments": mapped_segments,
    }
    validate_music_mapping_plan(plan)
    return plan


def validate_music_mapping_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("mode") != "energy_to_music_mapping_only":
        raise MusicEnergyMappingError("plan mode is invalid")
    if plan.get("music_build_started") is not False:
        raise MusicEnergyMappingError("music build must not be started")
    if plan.get("music_inserted") is not False:
        raise MusicEnergyMappingError("music must not be inserted")
    if plan.get("main_account_music_allowed") is not True:
        raise MusicEnergyMappingError("main account music must be allowed")
    if plan.get("uncut_music_allowed") is not False:
        raise MusicEnergyMappingError("uncut music must stay disabled")
    if plan.get("uncut_music_category") != "none":
        raise MusicEnergyMappingError("uncut music category must be none")
    if plan.get("channel_rules_enforced") is not True:
        raise MusicEnergyMappingError("channel rules must be enforced")
    segments = plan.get("segments")
    if not isinstance(segments, list):
        raise MusicEnergyMappingError("segments must be a list")
    for segment in segments:
        category = segment.get("music_category") if isinstance(segment, Mapping) else None
        if category not in ALLOWED_MUSIC_CATEGORIES:
            raise MusicEnergyMappingError(f"music category is not allowed: {category}")
        level = segment.get("energy_level") if isinstance(segment, Mapping) else None
        if level not in ALLOWED_ENERGY_LEVELS:
            raise MusicEnergyMappingError(f"energy level is not allowed: {level}")
    return dict(plan)


def build_empty_energy_mapping_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": "Phase 5.5",
        "step": "5.5-3",
        "mode": "energy_to_music_mapping_only",
        "phase_5_done": True,
        "p5_l_closed": True,
        "runtime_learning_locked": True,
        **_safe_default_flags(),
        "allowed_segment_roles": list(ALLOWED_SEGMENT_ROLES),
        "allowed_music_categories": list(ALLOWED_MUSIC_CATEGORIES),
        "allowed_energy_levels": list(ALLOWED_ENERGY_LEVELS),
        "allowed_mood_tags": list(ALLOWED_MOOD_TAGS),
        "allowed_channel_types": list(ALLOWED_CHANNEL_TYPES),
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "uncut_music_category": "none",
        "channel_rules_enforced": True,
        "ducking_is_flag_only": True,
        "writes_only_under": "reports/phase5_5_energy_to_music_mapping",
        "next_step": "5.5-4 Musik-Selector",
        "mapping_plan": {"mode": "energy_to_music_mapping_only", "segments": []},
        "warnings": [],
    }
