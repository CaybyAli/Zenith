from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


RENDER_PLAN_STATUS_READY = "render_plan_ready"
RENDER_PLAN_STATUS_READY_WITH_WARNINGS = "render_plan_ready_with_warnings"
RENDER_PLAN_STATUS_BLOCKED = "render_plan_blocked"
RENDER_PLAN_STATUS_FAILED = "render_plan_failed"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RenderPlanSource:
    source_id: str
    source_type: str
    path_hint: str | None = None
    track_id: str | None = None
    track_type: str | None = None
    required: bool = True
    available: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderPlanSegment:
    segment_id: str
    source_item_id: str | None = None
    source_segment_id: str | None = None
    source_start_seconds: float = 0.0
    source_end_seconds: float = 0.0
    output_start_seconds: float = 0.0
    output_end_seconds: float = 0.0
    duration_seconds: float = 0.0
    action: str = "keep"
    transition_intent: dict[str, Any] = field(default_factory=dict)
    censor_sfx_intent: dict[str, Any] = field(default_factory=dict)
    audio_mix_intent: dict[str, Any] = field(default_factory=dict)
    subtitle_intent: dict[str, Any] = field(default_factory=dict)
    protected: bool = False
    review_required: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderPlanOutputTarget:
    target_id: str
    target_format: str = "longform"
    container: str = "mp4"
    video_codec_intent: str = "h264"
    audio_codec_intent: str = "aac"
    resolution_intent: str = "1080p60"
    fps_intent: float = 60.0
    audio_lufs_intent: float = -14.0
    filename_hint: str | None = None
    output_path_hint: str | None = None
    platform: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderOperationIntent:
    intent_id: str
    intent_type: str
    description: str
    source_segment_id: str | None = None
    target_segment_id: str | None = None
    can_execute_now: bool = False
    requires_later_renderer: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderPlanReport:
    report_id: str
    job_id: str
    status: str
    sources: list[RenderPlanSource] = field(default_factory=list)
    segments: list[RenderPlanSegment] = field(default_factory=list)
    output_targets: list[RenderPlanOutputTarget] = field(default_factory=list)
    operation_intents: list[RenderOperationIntent] = field(default_factory=list)

    total_segments: int = 0
    total_duration_seconds: float = 0.0
    estimated_output_duration_seconds: float = 0.0

    dry_run_only: bool = True
    ready_for_renderer_contract: bool = False

    can_execute_plan: bool = False
    can_render: bool = False
    can_run_ffmpeg: bool = False
    can_write_media: bool = False
    can_apply_timeline: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)

        data["sources"] = [
            source.to_dict() if hasattr(source, "to_dict") else dict(source)
            for source in self.sources
        ]
        data["segments"] = [
            segment.to_dict() if hasattr(segment, "to_dict") else dict(segment)
            for segment in self.segments
        ]
        data["output_targets"] = [
            target.to_dict() if hasattr(target, "to_dict") else dict(target)
            for target in self.output_targets
        ]
        data["operation_intents"] = [
            intent.to_dict() if hasattr(intent, "to_dict") else dict(intent)
            for intent in self.operation_intents
        ]

        data["dry_run_only"] = True
        data["can_execute_plan"] = False
        data["can_render"] = False
        data["can_run_ffmpeg"] = False
        data["can_write_media"] = False
        data["can_apply_timeline"] = False

        return data


def build_render_plan_report(
    *,
    job_id: str,
    sources: list[RenderPlanSource] | None = None,
    segments: list[RenderPlanSegment] | None = None,
    output_targets: list[RenderPlanOutputTarget] | None = None,
    operation_intents: list[RenderOperationIntent] | None = None,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RenderPlanReport:
    safe_sources = list(sources or [])
    safe_segments = list(segments or [])
    safe_output_targets = list(output_targets or [])
    safe_operation_intents = list(operation_intents or [])
    safe_warnings = list(warnings or [])
    safe_blocking_reasons = list(blocking_reasons or [])

    total_duration = round(
        sum(max(0.0, float(segment.duration_seconds or 0.0)) for segment in safe_segments),
        3,
    )
    estimated_duration = round(
        max(
            [0.0]
            + [
                float(segment.output_end_seconds or 0.0)
                for segment in safe_segments
            ]
        ),
        3,
    )

    ready_for_contract = bool(
        safe_segments
        and safe_output_targets
        and not safe_blocking_reasons
        and total_duration > 0.0
    )

    if safe_blocking_reasons:
        status = RENDER_PLAN_STATUS_BLOCKED
        recommendation = "Render Plan blockiert. Blocking Reasons prüfen."
    elif safe_warnings:
        status = RENDER_PLAN_STATUS_READY_WITH_WARNINGS
        recommendation = "Render Plan ist als Dry-Run-Vertrag bereit, aber Warnungen prüfen."
    else:
        status = RENDER_PLAN_STATUS_READY
        recommendation = "Render Plan ist als Dry-Run-Vertrag bereit."

    return RenderPlanReport(
        report_id=f"render_plan_report_{job_id}",
        job_id=job_id,
        status=status,
        sources=safe_sources,
        segments=safe_segments,
        output_targets=safe_output_targets,
        operation_intents=safe_operation_intents,
        total_segments=len(safe_segments),
        total_duration_seconds=total_duration,
        estimated_output_duration_seconds=estimated_duration,
        dry_run_only=True,
        ready_for_renderer_contract=ready_for_contract,
        can_execute_plan=False,
        can_render=False,
        can_run_ffmpeg=False,
        can_write_media=False,
        can_apply_timeline=False,
        warnings=safe_warnings,
        blocking_reasons=safe_blocking_reasons,
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )
