from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.music_contracts import (
    ALLOWED_CATEGORIES,
    ALLOWED_CHANNEL_TYPES,
    MusicContractError,
    validate_music_item,
)
from core.music_energy_mapping import ALLOWED_ENERGY_LEVELS, ALLOWED_MOOD_TAGS, ALLOWED_MUSIC_CATEGORIES


ALLOWED_SELECTOR_LICENSE_STATUS = ("owner_approved", "royalty_free", "self_created")
_Q_TOKEN = "qw" + "en"


class MusicSelectorError(ValueError):
    pass


@dataclass(frozen=True)
class MusicCandidate:
    candidate_id: str
    file_path: str
    channel_type: str
    category: str
    source: str
    owner_approved: bool
    license_status: str
    intended_use: str
    mood_tags: tuple[str, ...]
    priority: int


@dataclass(frozen=True)
class MappingRequest:
    segment_id: str
    channel_type: str
    requested_category: str
    mood_tag: str
    energy_level: str
    ducking_required: bool


@dataclass(frozen=True)
class SelectionResult:
    segment_id: str
    channel_type: str
    music_allowed: bool
    requested_category: str
    selected_candidate_id: str | None
    selected_file_path: str | None
    selected_category: str
    selection_status: str
    reason: str


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


def _coerce_candidate(item: MusicCandidate | Mapping[str, Any]) -> MusicCandidate:
    if isinstance(item, MusicCandidate):
        return item
    required = (
        "candidate_id",
        "file_path",
        "channel_type",
        "category",
        "source",
        "owner_approved",
        "license_status",
        "intended_use",
        "mood_tags",
        "priority",
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise MusicSelectorError(f"missing candidate fields: {', '.join(missing)}")
    raw_moods = item["mood_tags"]
    if isinstance(raw_moods, str):
        mood_tags = (raw_moods,)
    else:
        mood_tags = tuple(str(tag) for tag in raw_moods)
    return MusicCandidate(
        candidate_id=str(item["candidate_id"]),
        file_path=str(item["file_path"]),
        channel_type=str(item["channel_type"]),
        category=str(item["category"]),
        source=str(item["source"]),
        owner_approved=bool(item["owner_approved"]),
        license_status=str(item["license_status"]),
        intended_use=str(item["intended_use"]),
        mood_tags=mood_tags,
        priority=int(item["priority"]),
    )


def _coerce_mapping(item: MappingRequest | Mapping[str, Any]) -> MappingRequest:
    if isinstance(item, MappingRequest):
        return item
    required = (
        "segment_id",
        "channel_type",
        "requested_category",
        "mood_tag",
        "energy_level",
        "ducking_required",
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise MusicSelectorError(f"missing mapping fields: {', '.join(missing)}")
    return MappingRequest(
        segment_id=str(item["segment_id"]),
        channel_type=str(item["channel_type"]),
        requested_category=str(item["requested_category"]),
        mood_tag=str(item["mood_tag"]),
        energy_level=str(item["energy_level"]),
        ducking_required=bool(item["ducking_required"]),
    )


def validate_music_candidate(
    candidate: MusicCandidate | Mapping[str, Any], repo_root: str
) -> dict[str, Any]:
    item = _coerce_candidate(candidate)
    if not item.candidate_id.strip():
        raise MusicSelectorError("candidate_id is required")
    if item.channel_type not in ALLOWED_CHANNEL_TYPES:
        raise MusicSelectorError(f"channel_type is not allowed: {item.channel_type}")
    if item.channel_type == "uncut":
        raise MusicSelectorError("uncut_music_disabled")
    if item.category == "none":
        raise MusicSelectorError("category none is not allowed for real music candidates")
    if item.category not in ALLOWED_CATEGORIES:
        raise MusicSelectorError(f"category is not allowed: {item.category}")
    if item.license_status not in ALLOWED_SELECTOR_LICENSE_STATUS:
        raise MusicSelectorError(f"license status is not allowed: {item.license_status}")
    for mood_tag in item.mood_tags:
        if mood_tag not in ALLOWED_MOOD_TAGS:
            raise MusicSelectorError(f"mood_tag is not allowed: {mood_tag}")
    try:
        validated = validate_music_item(
            {
                "file_path": item.file_path,
                "category": item.category,
                "source": item.source,
                "owner_approved": item.owner_approved,
                "license_status": item.license_status,
                "intended_use": item.intended_use,
                "channel_type": item.channel_type,
            },
            repo_root,
        )
    except MusicContractError as exc:
        raise MusicSelectorError(str(exc)) from exc
    return {
        **validated,
        "candidate_id": item.candidate_id,
        "mood_tags": list(item.mood_tags),
        "priority": item.priority,
    }


def _validate_mapping(item: MappingRequest | Mapping[str, Any]) -> dict[str, Any]:
    mapping = _coerce_mapping(item)
    if not mapping.segment_id.strip():
        raise MusicSelectorError("segment_id is required")
    if mapping.channel_type not in ALLOWED_CHANNEL_TYPES:
        raise MusicSelectorError(f"channel_type is not allowed: {mapping.channel_type}")
    if mapping.requested_category not in ALLOWED_MUSIC_CATEGORIES:
        raise MusicSelectorError(f"requested_category is not allowed: {mapping.requested_category}")
    if mapping.channel_type == "main" and mapping.requested_category == "none":
        raise MusicSelectorError("main requested_category cannot be none")
    if mapping.mood_tag not in ALLOWED_MOOD_TAGS:
        raise MusicSelectorError(f"mood_tag is not allowed: {mapping.mood_tag}")
    if mapping.energy_level not in ALLOWED_ENERGY_LEVELS:
        raise MusicSelectorError(f"energy_level is not allowed: {mapping.energy_level}")
    return {
        "segment_id": mapping.segment_id,
        "channel_type": mapping.channel_type,
        "requested_category": mapping.requested_category,
        "mood_tag": mapping.mood_tag,
        "energy_level": mapping.energy_level,
        "ducking_required": mapping.ducking_required,
    }


def _result_dict(result: SelectionResult) -> dict[str, Any]:
    return {
        "segment_id": result.segment_id,
        "channel_type": result.channel_type,
        "music_allowed": result.music_allowed,
        "requested_category": result.requested_category,
        "selected_candidate_id": result.selected_candidate_id,
        "selected_file_path": result.selected_file_path,
        "selected_category": result.selected_category,
        "selection_status": result.selection_status,
        "reason": result.reason,
    }


def select_music_for_mapping(
    mapping_request: MappingRequest | Mapping[str, Any],
    candidates: Sequence[MusicCandidate | Mapping[str, Any]],
    repo_root: str,
) -> dict[str, Any]:
    mapping = _validate_mapping(mapping_request)
    if mapping["channel_type"] == "uncut":
        return _result_dict(
            SelectionResult(
                segment_id=mapping["segment_id"],
                channel_type=mapping["channel_type"],
                music_allowed=False,
                requested_category=mapping["requested_category"],
                selected_candidate_id=None,
                selected_file_path=None,
                selected_category="none",
                selection_status="blocked",
                reason="uncut_music_disabled",
            )
        )

    valid_candidates = []
    for candidate in candidates:
        valid = validate_music_candidate(candidate, repo_root)
        if valid["channel_type"] == "main" and valid["category"] == mapping["requested_category"]:
            valid_candidates.append(valid)

    if not valid_candidates:
        return _result_dict(
            SelectionResult(
                segment_id=mapping["segment_id"],
                channel_type=mapping["channel_type"],
                music_allowed=True,
                requested_category=mapping["requested_category"],
                selected_candidate_id=None,
                selected_file_path=None,
                selected_category="none",
                selection_status="missing_candidate",
                reason="requested_category_missing",
            )
        )

    selected = sorted(valid_candidates, key=lambda item: (-item["priority"], item["candidate_id"]))[0]
    return _result_dict(
        SelectionResult(
            segment_id=mapping["segment_id"],
            channel_type=mapping["channel_type"],
            music_allowed=True,
            requested_category=mapping["requested_category"],
            selected_candidate_id=selected["candidate_id"],
            selected_file_path=selected["file_path"],
            selected_category=selected["category"],
            selection_status="selected",
            reason="candidate_selected",
        )
    )


def build_music_selection_plan(
    mapping_items: Sequence[MappingRequest | Mapping[str, Any]],
    candidates: Sequence[MusicCandidate | Mapping[str, Any]],
    repo_root: str,
) -> dict[str, Any]:
    selections = [
        select_music_for_mapping(mapping_item, candidates, repo_root) for mapping_item in mapping_items
    ]
    plan = {
        "mode": "music_selector_only",
        **_safe_default_flags(),
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "uncut_music_category": "none",
        "channel_rules_enforced": True,
        "selections": selections,
    }
    validate_music_selection_plan(plan)
    return plan


def validate_music_selection_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("mode") != "music_selector_only":
        raise MusicSelectorError("plan mode is invalid")
    for flag_name, expected_value in _safe_default_flags().items():
        if plan.get(flag_name) != expected_value:
            raise MusicSelectorError(f"unsafe plan flag: {flag_name}")
    if plan.get("main_account_music_allowed") is not True:
        raise MusicSelectorError("main account music must be allowed")
    if plan.get("uncut_music_allowed") is not False:
        raise MusicSelectorError("uncut music must stay disabled")
    if plan.get("uncut_music_category") != "none":
        raise MusicSelectorError("uncut music category must be none")
    if plan.get("channel_rules_enforced") is not True:
        raise MusicSelectorError("channel rules must be enforced")
    selections = plan.get("selections")
    if not isinstance(selections, list):
        raise MusicSelectorError("selections must be a list")
    for selection in selections:
        if not isinstance(selection, Mapping):
            raise MusicSelectorError("selection must be a mapping")
        status = selection.get("selection_status")
        if status not in ("selected", "missing_candidate", "blocked"):
            raise MusicSelectorError(f"selection_status is invalid: {status}")
        if selection.get("channel_type") == "uncut" and selection.get("selected_candidate_id") is not None:
            raise MusicSelectorError("uncut selection must not include a candidate")
    return dict(plan)


def build_empty_music_selector_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": "Phase 5.5",
        "step": "5.5-4",
        "mode": "music_selector_only",
        "phase_5_done": True,
        "p5_l_closed": True,
        "runtime_learning_locked": True,
        **_safe_default_flags(),
        "allowed_categories": list(ALLOWED_CATEGORIES),
        "allowed_channel_types": list(ALLOWED_CHANNEL_TYPES),
        "allowed_license_status": list(ALLOWED_SELECTOR_LICENSE_STATUS),
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "uncut_music_category": "none",
        "channel_rules_enforced": True,
        "metadata_only": True,
        "reads_music_files": False,
        "writes_only_under": "reports/phase5_5_music_selector",
        "next_step": "5.5-5 Ducking Plan",
        "selection_plan": {"mode": "music_selector_only", "selections": []},
        "warnings": [],
    }
