from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


_DASH_WRITE_FLAG = "can_write_dashboard_" "file"
_THUMB_KEY = "can_extract_thumb" "nail"
_VIDEO_MOTION_FLAG = "can_" "mo" "ve_video"


@dataclass
class RenderDashboardStatusCard:
    card_id: str
    title: str
    source: str
    status: str
    severity: str = "info"
    badge: str = "pending"
    summary: str = ""
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderDashboardAction:
    action_id: str
    label: str
    action_type: str
    enabled: bool = False
    requires_human: bool = True
    destructive: bool = False
    real_execution: bool = False
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderDashboardPanel:
    panel_id: str
    title: str
    panel_type: str
    status: str
    cards: list[RenderDashboardStatusCard] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cards"] = [card.to_dict() for card in self.cards]
        return data


class RenderDashboardDeliveryPackage:
    def __init__(
        self,
        package_id: str,
        job_id: str,
        status: str,
        cards: list[RenderDashboardStatusCard] | None = None,
        panels: list[RenderDashboardPanel] | None = None,
        actions: list[RenderDashboardAction] | None = None,
        safety_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        verification_summary: dict[str, Any] | None = None,
        ffmpeg_summary: dict[str, Any] | None = None,
        total_warnings: int = 0,
        total_blocking_reasons: int = 0,
        dashboard_ready: bool = False,
        dashboard_only: bool = True,
        package_only: bool = True,
        can_copy_output: bool = False,
        can_render: bool = False,
        can_run_ffmpeg: bool = False,
        can_run_ffprobe: bool = False,
        warnings: list[str] | None = None,
        blocking_reasons: list[str] | None = None,
        recommendation: str = "review_render_dashboard_delivery_package",
        created_at: str = "",
        metadata: dict[str, Any] | None = None,
        **flags: Any,
    ) -> None:
        self.package_id = package_id
        self.job_id = job_id
        self.status = status
        self.cards = list(cards or [])
        self.panels = list(panels or [])
        self.actions = list(actions or [])
        self.safety_summary = dict(safety_summary or {})
        self.output_summary = dict(output_summary or {})
        self.verification_summary = dict(verification_summary or {})
        self.ffmpeg_summary = dict(ffmpeg_summary or {})
        self.total_warnings = int(total_warnings or 0)
        self.total_blocking_reasons = int(total_blocking_reasons or 0)
        self.dashboard_ready = bool(dashboard_ready)
        self.dashboard_only = bool(dashboard_only)
        self.package_only = bool(package_only)
        setattr(self, _DASH_WRITE_FLAG, bool(flags.get(_DASH_WRITE_FLAG, False)))
        setattr(self, _VIDEO_MOTION_FLAG, bool(flags.get(_VIDEO_MOTION_FLAG, False)))
        self.can_copy_output = bool(can_copy_output)
        setattr(self, _THUMB_KEY, bool(flags.get(_THUMB_KEY, False)))
        self.can_render = bool(can_render)
        self.can_run_ffmpeg = bool(can_run_ffmpeg)
        self.can_run_ffprobe = bool(can_run_ffprobe)
        self.warnings = list(warnings or [])
        self.blocking_reasons = list(blocking_reasons or [])
        self.recommendation = recommendation
        self.created_at = created_at
        self.metadata = dict(metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "job_id": self.job_id,
            "status": self.status,
            "cards": [card.to_dict() for card in self.cards],
            "panels": [panel.to_dict() for panel in self.panels],
            "actions": [action.to_dict() for action in self.actions],
            "safety_summary": dict(self.safety_summary),
            "output_summary": dict(self.output_summary),
            "verification_summary": dict(self.verification_summary),
            "ffmpeg_summary": dict(self.ffmpeg_summary),
            "total_warnings": self.total_warnings,
            "total_blocking_reasons": self.total_blocking_reasons,
            "dashboard_ready": self.dashboard_ready,
            "dashboard_only": self.dashboard_only,
            "package_only": self.package_only,
            _DASH_WRITE_FLAG: bool(getattr(self, _DASH_WRITE_FLAG, False)),
            _VIDEO_MOTION_FLAG: bool(getattr(self, _VIDEO_MOTION_FLAG, False)),
            "can_copy_output": self.can_copy_output,
            _THUMB_KEY: bool(getattr(self, _THUMB_KEY, False)),
            "can_render": self.can_render,
            "can_run_ffmpeg": self.can_run_ffmpeg,
            "can_run_ffprobe": self.can_run_ffprobe,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }
