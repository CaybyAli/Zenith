from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


RENDER_BLUEPRINT_STATUS_READY = "render_blueprint_ready"
RENDER_BLUEPRINT_STATUS_READY_WITH_WARNINGS = "render_blueprint_ready_with_warnings"
RENDER_BLUEPRINT_STATUS_BLOCKED = "render_blueprint_blocked"
RENDER_BLUEPRINT_STATUS_FAILED = "render_blueprint_failed"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RenderBlueprintStep:
    step_id: str
    step_type: str
    order_index: int
    description: str
    source_segment_id: str | None = None
    target_segment_id: str | None = None
    planned_inputs: list[dict[str, Any]] = field(default_factory=list)
    planned_outputs: list[dict[str, Any]] = field(default_factory=list)
    filter_intents: list[dict[str, Any]] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    can_execute_now: bool = False
    requires_renderer_implementation: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)

        data["can_execute_now"] = False
        data["requires_renderer_implementation"] = True

        return data


@dataclass(slots=True)
class RenderBlueprintContract:
    contract_id: str
    job_id: str
    status: str
    blueprint_steps: list[RenderBlueprintStep] = field(default_factory=list)

    total_steps: int = 0
    trim_step_count: int = 0
    concat_step_count: int = 0
    transition_step_count: int = 0
    audio_mix_step_count: int = 0
    censor_sfx_step_count: int = 0
    subtitle_step_count: int = 0
    encode_step_count: int = 0

    dry_run_only: bool = True
    non_executable: bool = True
    ready_for_renderer_implementation: bool = False

    can_execute_contract: bool = False
    can_render: bool = False
    can_run_ffmpeg: bool = False
    can_spawn_process: bool = False
    can_write_media: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)

        data["blueprint_steps"] = [
            step.to_dict() if hasattr(step, "to_dict") else dict(step)
            for step in self.blueprint_steps
        ]

        data["total_steps"] = len(data["blueprint_steps"])

        data["dry_run_only"] = True
        data["non_executable"] = True

        data["can_execute_contract"] = False
        data["can_render"] = False
        data["can_run_ffmpeg"] = False
        data["can_spawn_process"] = False
        data["can_write_media"] = False

        return data


def build_render_blueprint_contract(
    *,
    job_id: str,
    blueprint_steps: list[RenderBlueprintStep] | None = None,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RenderBlueprintContract:
    safe_steps = list(blueprint_steps or [])
    safe_warnings = list(warnings or [])
    safe_blocking_reasons = list(blocking_reasons or [])

    trim_count = _count_steps(safe_steps, "trim")
    concat_count = _count_steps(safe_steps, "concat")
    transition_count = _count_steps(safe_steps, "transition")
    audio_mix_count = _count_steps(safe_steps, "audio_mix")
    censor_sfx_count = _count_steps(safe_steps, "censor_sfx")
    subtitle_count = _count_steps(safe_steps, "subtitle")
    encode_count = _count_steps(safe_steps, "encode")

    if safe_blocking_reasons:
        status = RENDER_BLUEPRINT_STATUS_BLOCKED
        recommendation = "Render Blueprint blockiert. Blocking Reasons pr?fen."
        ready_for_renderer = False
    elif safe_warnings:
        status = RENDER_BLUEPRINT_STATUS_READY_WITH_WARNINGS
        recommendation = "Render Blueprint ist bereit, aber Warnungen pr?fen."
        ready_for_renderer = True
    else:
        status = RENDER_BLUEPRINT_STATUS_READY
        recommendation = "Render Blueprint ist bereit f?r sp?tere Renderer-Implementierung."
        ready_for_renderer = True

    if not safe_steps:
        status = RENDER_BLUEPRINT_STATUS_BLOCKED
        recommendation = "Render Blueprint blockiert. Es wurden keine Blueprint Steps erzeugt."
        ready_for_renderer = False
        if "render_blueprint_steps_missing" not in safe_blocking_reasons:
            safe_blocking_reasons.append("render_blueprint_steps_missing")

    return RenderBlueprintContract(
        contract_id=f"render_blueprint_contract_{job_id}",
        job_id=job_id,
        status=status,
        blueprint_steps=safe_steps,
        total_steps=len(safe_steps),
        trim_step_count=trim_count,
        concat_step_count=concat_count,
        transition_step_count=transition_count,
        audio_mix_step_count=audio_mix_count,
        censor_sfx_step_count=censor_sfx_count,
        subtitle_step_count=subtitle_count,
        encode_step_count=encode_count,
        dry_run_only=True,
        non_executable=True,
        ready_for_renderer_implementation=ready_for_renderer,
        can_execute_contract=False,
        can_render=False,
        can_run_ffmpeg=False,
        can_spawn_process=False,
        can_write_media=False,
        warnings=safe_warnings,
        blocking_reasons=safe_blocking_reasons,
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )


def _count_steps(steps: list[RenderBlueprintStep], expected_type: str) -> int:
    return sum(1 for step in steps if step.step_type == expected_type)
