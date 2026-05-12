from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_SCENE_CHANGES = "skipped_no_scene_changes"
STATUS_FAILED = "failed"

CHANGE_TYPE_HARD = "hard_scene_change"
CHANGE_TYPE_SOFT = "soft_transition"
CHANGE_TYPE_FLASH = "flash_or_explosion_candidate"

SIGNAL_TYPE_HARD = "scene_hard_cut_point"
SIGNAL_TYPE_SOFT = "scene_soft_transition"
SIGNAL_TYPE_FLASH = "scene_flash_or_explosion_candidate"

SOURCE_SCENE_CHANGE = "scene_change"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _extract_scene_changes(scene_change_report: Any) -> list[dict[str, Any]]:
    report_dict = _safe_dict(scene_change_report)

    raw_changes = report_dict.get("scene_changes")
    if isinstance(raw_changes, list):
        return [dict(item) for item in raw_changes if isinstance(item, dict)]

    raw_changes = getattr(scene_change_report, "scene_changes", None)
    if isinstance(raw_changes, list):
        result: list[dict[str, Any]] = []
        for item in raw_changes:
            item_dict = _safe_dict(item)
            if item_dict:
                result.append(item_dict)
        return result

    return []


def _mapping_for_change_type(change_type: str) -> dict[str, str]:
    if change_type == CHANGE_TYPE_HARD:
        return {
            "signal_type": SIGNAL_TYPE_HARD,
            "action_hint": "candidate_cut_boundary",
            "priority": "high",
            "reason": "hard_scene_change_detected",
        }

    if change_type == CHANGE_TYPE_SOFT:
        return {
            "signal_type": SIGNAL_TYPE_SOFT,
            "action_hint": "avoid_hard_cut_or_review_transition",
            "priority": "medium",
            "reason": "soft_transition_detected",
        }

    if change_type == CHANGE_TYPE_FLASH:
        return {
            "signal_type": SIGNAL_TYPE_FLASH,
            "action_hint": "review_false_positive_scene_change",
            "priority": "medium",
            "reason": "flash_or_explosion_candidate_detected",
        }

    return {
        "signal_type": "scene_unknown_change",
        "action_hint": "review_scene_change",
        "priority": "low",
        "reason": "unknown_scene_change_detected",
    }


def build_scene_change_signal(
    scene_change: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any]:
    change_type = _safe_string(scene_change.get("change_type"), "unknown_scene_change")
    mapping = _mapping_for_change_type(change_type)

    center_seconds = max(0.0, _safe_float(scene_change.get("time_seconds"), 0.0))
    scene_score = max(0.0, min(1.0, _safe_float(scene_change.get("scene_score"), 0.0)))
    confidence = max(0.0, min(1.0, _safe_float(scene_change.get("confidence"), scene_score)))

    signal_type = mapping["signal_type"]

    return {
        "signal_id": f"scene_change_{source_index}_{signal_type}_{center_seconds:.3f}",
        "signal_type": signal_type,
        "source": SOURCE_SCENE_CHANGE,
        "start_seconds": center_seconds,
        "end_seconds": center_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": 0.0,
        "signal_score": scene_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": {
            "original_change_type": change_type,
            "frame_index": _safe_optional_int(scene_change.get("frame_index")),
            "is_false_positive_candidate": _safe_bool(
                scene_change.get("is_false_positive_candidate"),
                False,
            ),
            "scene_score": scene_score,
            "source_index": source_index,
            "warnings": _safe_list(scene_change.get("warnings")),
            "errors": _safe_list(scene_change.get("errors")),
        },
    }


@dataclass
class SceneChangeSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    hard_cut_signal_count: int = 0
    soft_transition_signal_count: int = 0
    false_positive_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "hard_cut_signal_count": self.hard_cut_signal_count,
            "soft_transition_signal_count": self.soft_transition_signal_count,
            "false_positive_signal_count": self.false_positive_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneChangeSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            hard_cut_signal_count=int(data.get("hard_cut_signal_count", 0) or 0),
            soft_transition_signal_count=int(
                data.get("soft_transition_signal_count", 0) or 0
            ),
            false_positive_signal_count=int(
                data.get("false_positive_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_scene_changes_to_signals(
    scene_changes: list[Any] | None,
) -> SceneChangeSignalAdapterResult:
    try:
        if not scene_changes:
            return SceneChangeSignalAdapterResult(
                status=STATUS_SKIPPED_NO_SCENE_CHANGES,
                signals=[],
                signal_count=0,
                recommendation="no_scene_changes_to_adapt",
            )

        signals: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, item in enumerate(scene_changes):
            item_dict = _safe_dict(item)
            if not item_dict:
                warnings.append(f"invalid_scene_change_entry_{index}")
                continue

            signal = build_scene_change_signal(item_dict, source_index=index)
            signals.append(signal)

        if not signals:
            return SceneChangeSignalAdapterResult(
                status=STATUS_SKIPPED_NO_SCENE_CHANGES,
                signals=[],
                signal_count=0,
                warnings=warnings,
                recommendation="no_valid_scene_changes_to_adapt",
            )

        hard_count = sum(1 for signal in signals if signal["signal_type"] == SIGNAL_TYPE_HARD)
        soft_count = sum(1 for signal in signals if signal["signal_type"] == SIGNAL_TYPE_SOFT)
        false_positive_count = sum(
            1
            for signal in signals
            if signal["signal_type"] == SIGNAL_TYPE_FLASH
            or bool(signal.get("metadata", {}).get("is_false_positive_candidate"))
        )

        status = STATUS_OK if not warnings else STATUS_COMPLETED_WITH_WARNINGS

        return SceneChangeSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            hard_cut_signal_count=hard_count,
            soft_transition_signal_count=soft_count,
            false_positive_signal_count=false_positive_count,
            warnings=warnings,
            errors=[],
            recommendation="scene_change_signals_available",
        )

    except Exception as exc:
        return SceneChangeSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=["scene_change_signal_adapter_failed"],
            recommendation="fix_scene_change_signal_adapter",
        )


def adapt_scene_change_report_to_signals(
    scene_change_report: Any,
) -> SceneChangeSignalAdapterResult:
    scene_changes = _extract_scene_changes(scene_change_report)
    return adapt_scene_changes_to_signals(scene_changes)
