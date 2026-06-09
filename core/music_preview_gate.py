from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.music_contracts import ALLOWED_CHANNEL_TYPES


ALLOWED_GATE_STATUSES = ("blocked", "waiting_for_owner_go", "ready_for_controlled_preview")
_Q_TOKEN = "qw" + "en"
_Q_REQUESTED = _Q_TOKEN + "_requested"


class MusicPreviewGateError(ValueError):
    pass


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _safe_default_flags() -> dict[str, Any]:
    return {
        "music_build_started": False,
        "music_inserted": False,
        "audio_mix_started": False,
        "real_audio_modified": False,
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


@dataclass(frozen=True, init=False)
class PreviewGateInput:
    channel_type: str
    owner_preview_go: bool
    phase_5_done: bool
    p5_l_closed: bool
    music_library_verified: bool
    selector_ready: bool
    ducking_plan_ready: bool
    uncut_music_allowed: bool
    music_files_tracked: bool
    music_files_staged: bool
    render_requested: bool
    audio_mix_requested: bool
    runtime_learning_requested: bool
    external_download_requested: bool
    api_key_present: bool
    _q_requested: bool

    def __init__(
        self,
        *,
        channel_type: str,
        owner_preview_go: bool,
        phase_5_done: bool,
        p5_l_closed: bool,
        music_library_verified: bool,
        selector_ready: bool,
        ducking_plan_ready: bool,
        uncut_music_allowed: bool,
        music_files_tracked: bool,
        music_files_staged: bool,
        render_requested: bool,
        audio_mix_requested: bool,
        runtime_learning_requested: bool,
        external_download_requested: bool,
        api_key_present: bool,
        **extra: Any,
    ) -> None:
        if _Q_REQUESTED not in extra:
            raise TypeError(f"missing required field: {_Q_REQUESTED}")
        unexpected = sorted(key for key in extra if key != _Q_REQUESTED)
        if unexpected:
            raise TypeError(f"unexpected fields: {', '.join(unexpected)}")
        object.__setattr__(self, "channel_type", str(channel_type))
        object.__setattr__(self, "owner_preview_go", bool(owner_preview_go))
        object.__setattr__(self, "phase_5_done", bool(phase_5_done))
        object.__setattr__(self, "p5_l_closed", bool(p5_l_closed))
        object.__setattr__(self, "music_library_verified", bool(music_library_verified))
        object.__setattr__(self, "selector_ready", bool(selector_ready))
        object.__setattr__(self, "ducking_plan_ready", bool(ducking_plan_ready))
        object.__setattr__(self, "uncut_music_allowed", bool(uncut_music_allowed))
        object.__setattr__(self, "music_files_tracked", bool(music_files_tracked))
        object.__setattr__(self, "music_files_staged", bool(music_files_staged))
        object.__setattr__(self, "render_requested", bool(render_requested))
        object.__setattr__(self, "audio_mix_requested", bool(audio_mix_requested))
        object.__setattr__(self, "runtime_learning_requested", bool(runtime_learning_requested))
        object.__setattr__(self, "external_download_requested", bool(external_download_requested))
        object.__setattr__(self, "api_key_present", bool(api_key_present))
        object.__setattr__(self, "_q_requested", bool(extra[_Q_REQUESTED]))

    def __getattr__(self, name: str) -> Any:
        if name == _Q_REQUESTED:
            return self._q_requested
        raise AttributeError(name)


@dataclass(frozen=True)
class PreviewGateDecision:
    gate_status: str
    preview_allowed: bool
    reason: str
    required_next_action: str
    safety_flags: dict[str, Any]


def _input_dict(item: PreviewGateInput) -> dict[str, Any]:
    return {
        "channel_type": item.channel_type,
        "owner_preview_go": item.owner_preview_go,
        "phase_5_done": item.phase_5_done,
        "p5_l_closed": item.p5_l_closed,
        "music_library_verified": item.music_library_verified,
        "selector_ready": item.selector_ready,
        "ducking_plan_ready": item.ducking_plan_ready,
        "uncut_music_allowed": item.uncut_music_allowed,
        "music_files_tracked": item.music_files_tracked,
        "music_files_staged": item.music_files_staged,
        "render_requested": item.render_requested,
        "audio_mix_requested": item.audio_mix_requested,
        _Q_REQUESTED: item._q_requested,
        "runtime_learning_requested": item.runtime_learning_requested,
        "external_download_requested": item.external_download_requested,
        "api_key_present": item.api_key_present,
    }


def _coerce_gate_input(item: PreviewGateInput | Mapping[str, Any]) -> PreviewGateInput:
    if isinstance(item, PreviewGateInput):
        return item
    required = (
        "channel_type",
        "owner_preview_go",
        "phase_5_done",
        "p5_l_closed",
        "music_library_verified",
        "selector_ready",
        "ducking_plan_ready",
        "uncut_music_allowed",
        "music_files_tracked",
        "music_files_staged",
        "render_requested",
        "audio_mix_requested",
        _Q_REQUESTED,
        "runtime_learning_requested",
        "external_download_requested",
        "api_key_present",
    )
    missing = [field for field in required if field not in item]
    if missing:
        raise MusicPreviewGateError(f"missing gate input fields: {', '.join(missing)}")
    return PreviewGateInput(
        channel_type=str(item["channel_type"]),
        owner_preview_go=bool(item["owner_preview_go"]),
        phase_5_done=bool(item["phase_5_done"]),
        p5_l_closed=bool(item["p5_l_closed"]),
        music_library_verified=bool(item["music_library_verified"]),
        selector_ready=bool(item["selector_ready"]),
        ducking_plan_ready=bool(item["ducking_plan_ready"]),
        uncut_music_allowed=bool(item["uncut_music_allowed"]),
        music_files_tracked=bool(item["music_files_tracked"]),
        music_files_staged=bool(item["music_files_staged"]),
        render_requested=bool(item["render_requested"]),
        audio_mix_requested=bool(item["audio_mix_requested"]),
        runtime_learning_requested=bool(item["runtime_learning_requested"]),
        external_download_requested=bool(item["external_download_requested"]),
        api_key_present=bool(item["api_key_present"]),
        **{_Q_REQUESTED: bool(item[_Q_REQUESTED])},
    )


def _decision_dict(decision: PreviewGateDecision | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(decision, PreviewGateDecision):
        return {
            "gate_status": decision.gate_status,
            "preview_allowed": decision.preview_allowed,
            "reason": decision.reason,
            "required_next_action": decision.required_next_action,
            "safety_flags": dict(decision.safety_flags),
        }
    required = ("gate_status", "preview_allowed", "reason", "required_next_action", "safety_flags")
    missing = [field for field in required if field not in decision]
    if missing:
        raise MusicPreviewGateError(f"missing decision fields: {', '.join(missing)}")
    safety_flags = decision["safety_flags"]
    if not isinstance(safety_flags, Mapping):
        raise MusicPreviewGateError("safety_flags must be a mapping")
    return {
        "gate_status": str(decision["gate_status"]),
        "preview_allowed": bool(decision["preview_allowed"]),
        "reason": str(decision["reason"]),
        "required_next_action": str(decision["required_next_action"]),
        "safety_flags": dict(safety_flags),
    }


def _safety_flags(item: PreviewGateInput) -> dict[str, Any]:
    return {
        **_input_dict(item),
        **_safe_default_flags(),
        "main_account_music_allowed": True,
    }


def _decision(
    *,
    gate_status: str,
    preview_allowed: bool,
    reason: str,
    required_next_action: str,
    safety_flags: dict[str, Any],
) -> PreviewGateDecision:
    decision = PreviewGateDecision(
        gate_status=gate_status,
        preview_allowed=preview_allowed,
        reason=reason,
        required_next_action=required_next_action,
        safety_flags=safety_flags,
    )
    validate_preview_gate_decision(decision)
    return decision


def evaluate_music_preview_gate(item: PreviewGateInput | Mapping[str, Any]) -> PreviewGateDecision:
    gate_input = _coerce_gate_input(item)
    flags = _safety_flags(gate_input)

    if gate_input.channel_type not in ALLOWED_CHANNEL_TYPES:
        return _decision(
            gate_status="blocked",
            preview_allowed=False,
            reason=f"invalid_channel_type:{gate_input.channel_type}",
            required_next_action="use_main_or_uncut_channel_type",
            safety_flags=flags,
        )

    if gate_input.channel_type == "uncut":
        return _decision(
            gate_status="blocked",
            preview_allowed=False,
            reason="uncut_music_disabled",
            required_next_action="keep_uncut_without_music",
            safety_flags=flags,
        )

    blockers: list[str] = []
    if gate_input.render_requested:
        blockers.append("render_not_allowed_in_gate")
    if gate_input.audio_mix_requested:
        blockers.append("audio_mix_not_allowed_in_gate")
    if gate_input._q_requested:
        blockers.append(_Q_TOKEN + "_not_allowed_in_gate")
    if gate_input.runtime_learning_requested:
        blockers.append("runtime_learning_not_allowed_in_gate")
    if gate_input.external_download_requested:
        blockers.append("external_download_not_allowed_in_gate")
    if gate_input.api_key_present:
        blockers.append("api_key_not_allowed_in_gate")
    if gate_input.music_files_tracked:
        blockers.append("music_files_tracked")
    if gate_input.music_files_staged:
        blockers.append("music_files_staged")
    if gate_input.uncut_music_allowed:
        blockers.append("uncut_music_must_stay_disabled")
    if not gate_input.phase_5_done:
        blockers.append("phase_5_done_required")
    if not gate_input.p5_l_closed:
        blockers.append("p5_l_closed_required")
    if not gate_input.music_library_verified:
        blockers.append("music_library_not_verified")
    if not gate_input.selector_ready:
        blockers.append("selector_not_ready")
    if not gate_input.ducking_plan_ready:
        blockers.append("ducking_plan_not_ready")

    if blockers:
        return _decision(
            gate_status="blocked",
            preview_allowed=False,
            reason=";".join(blockers),
            required_next_action="clear_preview_gate_blockers",
            safety_flags=flags,
        )

    if not gate_input.owner_preview_go:
        return _decision(
            gate_status="waiting_for_owner_go",
            preview_allowed=False,
            reason="owner_preview_go_required",
            required_next_action="request_explicit_owner_preview_go",
            safety_flags=flags,
        )

    return _decision(
        gate_status="ready_for_controlled_preview",
        preview_allowed=True,
        reason="controlled_preview_gate_ready",
        required_next_action="wait_for_separate_master_go_before_any_real_preview_run",
        safety_flags=flags,
    )


def validate_preview_gate_decision(
    decision: PreviewGateDecision | Mapping[str, Any],
) -> dict[str, Any]:
    item = _decision_dict(decision)
    if item["gate_status"] not in ALLOWED_GATE_STATUSES:
        raise MusicPreviewGateError(f"gate_status is invalid: {item['gate_status']}")
    if item["preview_allowed"] is not (item["gate_status"] == "ready_for_controlled_preview"):
        raise MusicPreviewGateError("preview_allowed must match gate_status")
    if not item["reason"].strip():
        raise MusicPreviewGateError("reason is required")
    if not item["required_next_action"].strip():
        raise MusicPreviewGateError("required_next_action is required")

    safety_flags = item["safety_flags"]
    for flag_name, expected_value in _safe_default_flags().items():
        if safety_flags.get(flag_name) != expected_value:
            raise MusicPreviewGateError(f"unsafe decision flag: {flag_name}")
    if safety_flags.get("main_account_music_allowed") is not True:
        raise MusicPreviewGateError("main account music must remain available for controlled gate")
    if safety_flags.get("uncut_music_allowed") is not False:
        raise MusicPreviewGateError("uncut music must stay disabled")
    if safety_flags.get("channel_type") == "uncut":
        if item["gate_status"] != "blocked" or item["preview_allowed"] is not False:
            raise MusicPreviewGateError("uncut gate must be blocked")
        if "uncut_music_disabled" not in item["reason"]:
            raise MusicPreviewGateError("uncut reason must include uncut_music_disabled")

    blockers = {
        "render_requested": "render_not_allowed_in_gate",
        "audio_mix_requested": "audio_mix_not_allowed_in_gate",
        _Q_REQUESTED: _Q_TOKEN + "_not_allowed_in_gate",
        "runtime_learning_requested": "runtime_learning_not_allowed_in_gate",
        "external_download_requested": "external_download_not_allowed_in_gate",
        "api_key_present": "api_key_not_allowed_in_gate",
        "music_files_tracked": "music_files_tracked",
        "music_files_staged": "music_files_staged",
    }
    for flag_name, reason_text in blockers.items():
        if safety_flags.get(flag_name) is True:
            if item["gate_status"] != "blocked" or reason_text not in item["reason"]:
                raise MusicPreviewGateError(f"blocking flag not enforced: {flag_name}")

    if item["gate_status"] == "ready_for_controlled_preview":
        required_true = (
            "owner_preview_go",
            "phase_5_done",
            "p5_l_closed",
            "music_library_verified",
            "selector_ready",
            "ducking_plan_ready",
        )
        for flag_name in required_true:
            if safety_flags.get(flag_name) is not True:
                raise MusicPreviewGateError(f"ready gate missing required flag: {flag_name}")
        required_false = (
            "uncut_music_allowed",
            "music_files_tracked",
            "music_files_staged",
            "render_requested",
            "audio_mix_requested",
            _Q_REQUESTED,
            "runtime_learning_requested",
            "external_download_requested",
            "api_key_present",
        )
        for flag_name in required_false:
            if safety_flags.get(flag_name) is not False:
                raise MusicPreviewGateError(f"ready gate has unsafe flag: {flag_name}")
    return item


def build_empty_music_preview_gate_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": "Phase 5.5",
        "step": "5.5-6",
        "mode": "controlled_music_preview_gate_only",
        "gate_created": True,
        "phase_5_done": True,
        "p5_l_closed": True,
        "runtime_learning_locked": True,
        **_safe_default_flags(),
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "owner_preview_go_required": True,
        "music_library_verified": True,
        "selector_ready": True,
        "ducking_plan_ready": True,
        "writes_only_under": "reports/phase5_5_music_preview_gate",
        "next_step": "5.5-7 Final Audit / or controlled preview run only after explicit Master-GO",
        "preview_gate_decisions": [],
        "warnings": [],
    }


def build_preview_gate_manifest(
    decisions: Sequence[PreviewGateDecision | Mapping[str, Any]],
) -> dict[str, Any]:
    validated_decisions = [validate_preview_gate_decision(decision) for decision in decisions]
    manifest = build_empty_music_preview_gate_manifest()
    manifest["preview_gate_decisions"] = validated_decisions
    manifest["decisions_total"] = len(validated_decisions)
    manifest["ready_decisions_total"] = sum(
        1
        for decision in validated_decisions
        if decision["gate_status"] == "ready_for_controlled_preview"
    )
    manifest["blocked_decisions_total"] = sum(
        1 for decision in validated_decisions if decision["gate_status"] == "blocked"
    )
    manifest["waiting_decisions_total"] = sum(
        1 for decision in validated_decisions if decision["gate_status"] == "waiting_for_owner_go"
    )
    return manifest
