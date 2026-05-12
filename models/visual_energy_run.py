from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.visual_energy import VisualEnergyResult


VISUAL_ENERGY_RUN_STATUS_OK = "ok"
VISUAL_ENERGY_RUN_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
VISUAL_ENERGY_RUN_STATUS_SKIPPED_NO_VISUAL_SOURCES = "skipped_no_visual_sources"
VISUAL_ENERGY_RUN_STATUS_FAILED = "failed"


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


@dataclass
class VisualEnergyRunReport:
    status: str
    source: str = "visual_energy_runner"
    visual_energy_result: VisualEnergyResult | None = None
    visual_energy_points: list[dict[str, Any]] = field(default_factory=list)
    visual_energy_segments: list[dict[str, Any]] = field(default_factory=list)
    point_count: int = 0
    segment_count: int = 0
    high_energy_segment_count: int = 0
    low_energy_segment_count: int = 0
    technical_warning_segment_count: int = 0
    duration_seconds: float | None = None
    frame_sample_rate: float = 2.0
    recommendation: str = "review_visual_energy_timeline"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "visual_energy_result": (
                self.visual_energy_result.to_dict()
                if self.visual_energy_result
                else None
            ),
            "visual_energy_points": [
                dict(item) for item in self.visual_energy_points
            ],
            "visual_energy_segments": [
                dict(item) for item in self.visual_energy_segments
            ],
            "point_count": self.point_count,
            "segment_count": self.segment_count,
            "high_energy_segment_count": self.high_energy_segment_count,
            "low_energy_segment_count": self.low_energy_segment_count,
            "technical_warning_segment_count": self.technical_warning_segment_count,
            "duration_seconds": self.duration_seconds,
            "frame_sample_rate": self.frame_sample_rate,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "VisualEnergyRunReport":
        if not isinstance(data, dict):
            data = {}

        visual_energy_result_data = data.get("visual_energy_result")
        visual_energy_result = None
        if isinstance(visual_energy_result_data, dict):
            visual_energy_result = VisualEnergyResult.from_dict(
                visual_energy_result_data
            )

        return cls(
            status=_safe_string(data.get("status"), VISUAL_ENERGY_RUN_STATUS_FAILED),
            source=_safe_string(data.get("source"), "visual_energy_runner"),
            visual_energy_result=visual_energy_result,
            visual_energy_points=_safe_dict_list(data.get("visual_energy_points")),
            visual_energy_segments=_safe_dict_list(data.get("visual_energy_segments")),
            point_count=_safe_int(data.get("point_count"), 0),
            segment_count=_safe_int(data.get("segment_count"), 0),
            high_energy_segment_count=_safe_int(
                data.get("high_energy_segment_count"),
                0,
            ),
            low_energy_segment_count=_safe_int(
                data.get("low_energy_segment_count"),
                0,
            ),
            technical_warning_segment_count=_safe_int(
                data.get("technical_warning_segment_count"),
                0,
            ),
            duration_seconds=_safe_optional_float(data.get("duration_seconds")),
            frame_sample_rate=_safe_float(data.get("frame_sample_rate"), 2.0),
            recommendation=_safe_string(
                data.get("recommendation"),
                "review_visual_energy_timeline",
            ),
            warnings=_safe_string_list(data.get("warnings")),
            errors=_safe_string_list(data.get("errors")),
            metadata=_safe_dict(data.get("metadata")),
        )
