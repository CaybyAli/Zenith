from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.music_contracts import ALLOWED_CATEGORIES, ALLOWED_CHANNEL_TYPES
from core.music_energy_mapping import ALLOWED_MOOD_TAGS


ALLOWED_DUCKING_CATEGORIES = (*ALLOWED_CATEGORIES, "none")
ALLOWED_SELECTION_STATUSES = ("selected", "missing_candidate", "blocked", "no_selected_music")
ALLOWED_SPEECH_PRIORITIES = ("low", "medium", "high", "very_high")
ALLOWED_PLAN_STATUSES = ("planned", "no_selected_music", "blocked")
LOUD_CATEGORY_LIMIT_DB = -14.0
_Q_TOKEN = "qw" + "en"


class MusicDuckingPlanError(ValueError):
    pass


@dataclass(frozen=True)
class DuckingInput:
    segment_id: str
    channel_type: str
    selected_category: str
    selection_status: str
    selected_candidate_id: str | None
    speech_density: float
    energy_score: float
    highlight_score: float
    mood_tag: str


@dataclass(frozen=True)
class DuckingPlanItem:
    segment_id: str
    channel_type: str
    music_allowed: bool
    selected_category: str
    ducking_enabled: bool
    base_music_gain_db: float | None
    ducking_gain_db: float | None
    max_music_gain_db: float | None
    speech_priority: str
    plan_status: str
    reason: str


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _safe_default_flags() -> dict[str, Any]:
    return {
        "music_build_started": False,
        "music_inserted": False,
        "audio_mix_started": False,
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
        "real_audio_modified": False,
    }


def _validate_score(name: str, value: float) -> float:
    score = float(value)
    if score < 0.0 or score > 1.0:
        raise MusicDuckingPlanError(f"{name} must be between 0.0 and 1.0")
    return score


def classify_speech_priority(speech_density: float) -> str:
    density = _validate_score("speech_density", speech_density)
    if density >= 0.70:
        return "very_high"
    if density >= 0.45:
        return "high"
    if density >= 0.20:
        return "medium"
    return "low"


def _coerce_ducking_input(item: DuckingInput | Mapping[str, Any]) -> DuckingInput:
    if isinstance(item, DuckingInput):
        return item
    required = (
        "segment_id",
        "channel_type",
        "selected_category",
        "selection_status",
        "selected_candidate_id",
        "speech_density",
        "energy_score",
        "highlight_score",
        "mood_tag",
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise MusicDuckingPlanError(f"missing ducking input fields: {', '.join(missing)}")
    candidate = item["selected_candidate_id"]
    return DuckingInput(
        segment_id=str(item["segment_id"]),
        channel_type=str(item["channel_type"]),
        selected_category=str(item["selected_category"]),
        selection_status=str(item["selection_status"]),
        selected_candidate_id=None if candidate is None else str(candidate),
        speech_density=float(item["speech_density"]),
        energy_score=float(item["energy_score"]),
        highlight_score=float(item["highlight_score"]),
        mood_tag=str(item["mood_tag"]),
    )


def _coerce_plan_item(item: DuckingPlanItem | Mapping[str, Any]) -> DuckingPlanItem:
    if isinstance(item, DuckingPlanItem):
        return item
    required = (
        "segment_id",
        "channel_type",
        "music_allowed",
        "selected_category",
        "ducking_enabled",
        "base_music_gain_db",
        "ducking_gain_db",
        "max_music_gain_db",
        "speech_priority",
        "plan_status",
        "reason",
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise MusicDuckingPlanError(f"missing ducking plan fields: {', '.join(missing)}")
    return DuckingPlanItem(
        segment_id=str(item["segment_id"]),
        channel_type=str(item["channel_type"]),
        music_allowed=bool(item["music_allowed"]),
        selected_category=str(item["selected_category"]),
        ducking_enabled=bool(item["ducking_enabled"]),
        base_music_gain_db=(
            None if item["base_music_gain_db"] is None else float(item["base_music_gain_db"])
        ),
        ducking_gain_db=(
            None if item["ducking_gain_db"] is None else float(item["ducking_gain_db"])
        ),
        max_music_gain_db=(
            None if item["max_music_gain_db"] is None else float(item["max_music_gain_db"])
        ),
        speech_priority=str(item["speech_priority"]),
        plan_status=str(item["plan_status"]),
        reason=str(item["reason"]),
    )


def _validate_ducking_input(item: DuckingInput | Mapping[str, Any]) -> DuckingInput:
    ducking_input = _coerce_ducking_input(item)
    if not ducking_input.segment_id.strip():
        raise MusicDuckingPlanError("segment_id is required")
    if ducking_input.channel_type not in ALLOWED_CHANNEL_TYPES:
        raise MusicDuckingPlanError(f"channel_type is not allowed: {ducking_input.channel_type}")
    if ducking_input.selected_category not in ALLOWED_DUCKING_CATEGORIES:
        raise MusicDuckingPlanError(
            f"selected_category is not allowed: {ducking_input.selected_category}"
        )
    if ducking_input.channel_type == "main" and ducking_input.selection_status == "selected":
        if ducking_input.selected_category == "none":
            raise MusicDuckingPlanError("selected main music must include a category")
        if not ducking_input.selected_candidate_id:
            raise MusicDuckingPlanError("selected main music must include a candidate")
    if ducking_input.mood_tag not in ALLOWED_MOOD_TAGS:
        raise MusicDuckingPlanError(f"mood_tag is not allowed: {ducking_input.mood_tag}")
    _validate_score("speech_density", ducking_input.speech_density)
    _validate_score("energy_score", ducking_input.energy_score)
    _validate_score("highlight_score", ducking_input.highlight_score)
    return ducking_input


def _gain_profile(speech_priority: str) -> tuple[float, float, float]:
    if speech_priority == "very_high":
        return -26.0, -34.0, -24.0
    if speech_priority == "high":
        return -23.0, -30.0, -21.0
    if speech_priority == "medium":
        return -20.0, -26.0, -18.0
    if speech_priority == "low":
        return -27.0, -32.0, -25.0
    raise MusicDuckingPlanError(f"speech_priority is invalid: {speech_priority}")


def _item_dict(item: DuckingPlanItem) -> dict[str, Any]:
    return {
        "segment_id": item.segment_id,
        "channel_type": item.channel_type,
        "music_allowed": item.music_allowed,
        "selected_category": item.selected_category,
        "ducking_enabled": item.ducking_enabled,
        "base_music_gain_db": item.base_music_gain_db,
        "ducking_gain_db": item.ducking_gain_db,
        "max_music_gain_db": item.max_music_gain_db,
        "speech_priority": item.speech_priority,
        "plan_status": item.plan_status,
        "reason": item.reason,
    }


def build_ducking_plan_item(item: DuckingInput | Mapping[str, Any]) -> dict[str, Any]:
    ducking_input = _validate_ducking_input(item)
    speech_priority = classify_speech_priority(ducking_input.speech_density)

    if ducking_input.channel_type == "uncut":
        return _item_dict(
            DuckingPlanItem(
                segment_id=ducking_input.segment_id,
                channel_type="uncut",
                music_allowed=False,
                selected_category="none",
                ducking_enabled=False,
                base_music_gain_db=None,
                ducking_gain_db=None,
                max_music_gain_db=None,
                speech_priority=speech_priority,
                plan_status="blocked",
                reason="uncut_music_disabled",
            )
        )

    if ducking_input.selection_status != "selected" or not ducking_input.selected_candidate_id:
        return _item_dict(
            DuckingPlanItem(
                segment_id=ducking_input.segment_id,
                channel_type="main",
                music_allowed=False,
                selected_category="none",
                ducking_enabled=False,
                base_music_gain_db=None,
                ducking_gain_db=None,
                max_music_gain_db=None,
                speech_priority=speech_priority,
                plan_status="no_selected_music",
                reason="no_selected_music",
            )
        )

    base_gain, ducking_gain, max_gain = _gain_profile(speech_priority)
    plan_item = DuckingPlanItem(
        segment_id=ducking_input.segment_id,
        channel_type="main",
        music_allowed=True,
        selected_category=ducking_input.selected_category,
        ducking_enabled=True,
        base_music_gain_db=base_gain,
        ducking_gain_db=ducking_gain,
        max_music_gain_db=max_gain,
        speech_priority=speech_priority,
        plan_status="planned",
        reason=f"speech_priority_{speech_priority}_ducking_planned",
    )
    return validate_ducking_plan_item(plan_item)


def validate_ducking_plan_item(item: DuckingPlanItem | Mapping[str, Any]) -> dict[str, Any]:
    plan_item = _coerce_plan_item(item)
    if not plan_item.segment_id.strip():
        raise MusicDuckingPlanError("segment_id is required")
    if plan_item.channel_type not in ALLOWED_CHANNEL_TYPES:
        raise MusicDuckingPlanError(f"channel_type is not allowed: {plan_item.channel_type}")
    if plan_item.selected_category not in ALLOWED_DUCKING_CATEGORIES:
        raise MusicDuckingPlanError(
            f"selected_category is not allowed: {plan_item.selected_category}"
        )
    if plan_item.speech_priority not in ALLOWED_SPEECH_PRIORITIES:
        raise MusicDuckingPlanError(f"speech_priority is invalid: {plan_item.speech_priority}")
    if plan_item.plan_status not in ALLOWED_PLAN_STATUSES:
        raise MusicDuckingPlanError(f"plan_status is invalid: {plan_item.plan_status}")
    if not plan_item.reason.strip():
        raise MusicDuckingPlanError("reason is required")

    gain_values = (
        plan_item.base_music_gain_db,
        plan_item.ducking_gain_db,
        plan_item.max_music_gain_db,
    )
    if plan_item.music_allowed is False or plan_item.ducking_enabled is False:
        if any(value is not None for value in gain_values):
            raise MusicDuckingPlanError("disabled music plan must not include gain values")
    else:
        if any(value is None for value in gain_values):
            raise MusicDuckingPlanError("enabled ducking plan must include gain values")
        assert plan_item.base_music_gain_db is not None
        assert plan_item.ducking_gain_db is not None
        assert plan_item.max_music_gain_db is not None
        if plan_item.ducking_gain_db > plan_item.base_music_gain_db:
            raise MusicDuckingPlanError("ducking gain must not be louder than base gain")
        if plan_item.base_music_gain_db > plan_item.max_music_gain_db:
            raise MusicDuckingPlanError("base gain must not exceed max gain")

    for value in gain_values:
        if value is not None and value > 0.0:
            raise MusicDuckingPlanError("gain values must not be positive")
    if plan_item.max_music_gain_db is not None and plan_item.max_music_gain_db > LOUD_CATEGORY_LIMIT_DB:
        raise MusicDuckingPlanError("max_music_gain_db must not exceed -14.0")

    if plan_item.channel_type == "uncut":
        if plan_item.music_allowed is not False:
            raise MusicDuckingPlanError("uncut music must stay disabled")
        if plan_item.selected_category != "none":
            raise MusicDuckingPlanError("uncut selected_category must be none")
        if plan_item.ducking_enabled is not False:
            raise MusicDuckingPlanError("uncut ducking must stay disabled")
        if plan_item.plan_status != "blocked":
            raise MusicDuckingPlanError("uncut plan_status must be blocked")
        if "uncut_music_disabled" not in plan_item.reason:
            raise MusicDuckingPlanError("uncut reason must include uncut_music_disabled")

    if plan_item.plan_status == "no_selected_music":
        if plan_item.music_allowed is not False or plan_item.ducking_enabled is not False:
            raise MusicDuckingPlanError("no_selected_music must not enable music")
        if plan_item.selected_category != "none":
            raise MusicDuckingPlanError("no_selected_music selected_category must be none")

    return _item_dict(plan_item)


def build_ducking_plan(inputs: Sequence[DuckingInput | Mapping[str, Any]]) -> dict[str, Any]:
    items = [build_ducking_plan_item(item) for item in inputs]
    plan = {
        "mode": "ducking_plan_only",
        "music_build_started": False,
        "music_inserted": False,
        "audio_mix_started": False,
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "speech_priority_enforced": True,
        "items": items,
    }
    return validate_ducking_plan(plan)


def validate_ducking_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("mode") != "ducking_plan_only":
        raise MusicDuckingPlanError("plan mode is invalid")
    for flag in ("music_build_started", "music_inserted", "audio_mix_started"):
        if plan.get(flag) is not False:
            raise MusicDuckingPlanError(f"unsafe plan flag: {flag}")
    if plan.get("main_account_music_allowed") is not True:
        raise MusicDuckingPlanError("main account music must be allowed")
    if plan.get("uncut_music_allowed") is not False:
        raise MusicDuckingPlanError("uncut music must stay disabled")
    if plan.get("speech_priority_enforced") is not True:
        raise MusicDuckingPlanError("speech priority must be enforced")
    items = plan.get("items")
    if not isinstance(items, list):
        raise MusicDuckingPlanError("items must be a list")
    validated_items = [validate_ducking_plan_item(item) for item in items]
    return {**dict(plan), "items": validated_items}


def build_empty_ducking_plan_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": "Phase 5.5",
        "step": "5.5-5",
        "mode": "ducking_plan_only",
        "phase_5_done": True,
        "p5_l_closed": True,
        "runtime_learning_locked": True,
        **_safe_default_flags(),
        "allowed_categories": list(ALLOWED_DUCKING_CATEGORIES),
        "allowed_channel_types": list(ALLOWED_CHANNEL_TYPES),
        "allowed_speech_priorities": list(ALLOWED_SPEECH_PRIORITIES),
        "allowed_selection_statuses": list(ALLOWED_SELECTION_STATUSES),
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "uncut_music_category": "none",
        "ducking_plan_created": True,
        "speech_priority_enforced": True,
        "writes_only_under": "reports/phase5_5_ducking_plan",
        "next_step": "5.5-6 Controlled Music Preview Gate",
        "ducking_plan": {"mode": "ducking_plan_only", "items": []},
        "warnings": [],
    }
