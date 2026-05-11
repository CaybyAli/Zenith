from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from models.audio_normalization_signal import AudioNormalizationSignalAdapterResult


SOURCE = "audio_normalization_signal_adapter"

SIGNAL_TYPE_BY_LEVEL_STATUS = {
    "too_quiet": "audio_gain_boost_recommended",
    "too_loud": "audio_gain_reduce_recommended",
    "clipped": "audio_clipping_warning",
    "silent": "audio_silent_warning",
}

SCORE_BY_LEVEL_STATUS = {
    "clipped": 1.0,
    "silent": 0.9,
    "too_quiet": 0.8,
    "too_loud": 0.8,
}

PLAN_KEYS = {
    "level_status",
    "audio_level_status",
    "normalization_needed",
    "recommended_gain_db",
    "limited_gain_db",
    "target_rms_dbfs",
    "target_peak_dbfs",
    "reason",
}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "y", "needed", "normalization_needed"}:
            return True
        if text in {"false", "0", "no", "n", "not_needed", "none"}:
            return False

    return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if is_dataclass(value):
        try:
            return asdict(value)
        except Exception:
            return {}

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            data = to_dict()
            if isinstance(data, dict):
                return dict(data)
        except Exception:
            return {}

    return {}


def _read_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _is_plan_like(data: dict[str, Any]) -> bool:
    return bool(PLAN_KEYS.intersection(set(data.keys())))


def _normalize_level_status(value: Any) -> str:
    text = _safe_str(value, "normal").strip().lower()
    text = text.replace("-", "_").replace(" ", "_")

    if text in {"ok", "none", "clean", "no_change", "not_needed"}:
        return "normal"

    return text or "normal"


def _infer_normalization_needed(plan: dict[str, Any], level_status: str) -> bool:
    if "normalization_needed" in plan:
        return _safe_bool(plan.get("normalization_needed"), False)

    if level_status in {"too_quiet", "too_loud", "clipped", "silent"}:
        return True

    gain = _safe_float(plan.get("recommended_gain_db"), 0.0) or 0.0
    return abs(gain) > 0.05


def _clean_plan_dict(data: dict[str, Any]) -> dict[str, Any]:
    level_status = _normalize_level_status(
        data.get("level_status", data.get("audio_level_status", data.get("status", "normal")))
    )

    cleaned = dict(data)
    cleaned["level_status"] = level_status
    cleaned["recommended_gain_db"] = _safe_float(data.get("recommended_gain_db"), None)
    cleaned["limited_gain_db"] = _safe_float(data.get("limited_gain_db"), None)
    cleaned["target_rms_dbfs"] = _safe_float(data.get("target_rms_dbfs"), None)
    cleaned["target_peak_dbfs"] = _safe_float(data.get("target_peak_dbfs"), None)
    cleaned["normalization_needed"] = _infer_normalization_needed(cleaned, level_status)
    cleaned["reason"] = _safe_str(data.get("reason"), "")

    return cleaned


def extract_audio_normalization_plan_dict(value: Any) -> dict[str, Any] | None:
    return _extract_audio_normalization_plan_dict(value, seen_ids=set())


def _extract_audio_normalization_plan_dict(value: Any, seen_ids: set[int]) -> dict[str, Any] | None:
    if value is None:
        return None

    value_id = id(value)
    if value_id in seen_ids:
        return None
    seen_ids.add(value_id)

    if isinstance(value, dict):
        data = dict(value)

        if _is_plan_like(data):
            return _clean_plan_dict(data)

        nested_keys = [
            "normalization_result",
            "audio_normalization_report",
            "normalization_report",
            "audio_normalization_plan",
            "normalization_plan",
            "plan",
            "result",
            "report",
        ]

        for key in nested_keys:
            if key in data:
                found = _extract_audio_normalization_plan_dict(data.get(key), seen_ids)
                if found is not None:
                    return found

        return None

    data = _safe_dict(value)
    if data:
        found = _extract_audio_normalization_plan_dict(data, seen_ids)
        if found is not None:
            return found

    attr_keys = [
        "normalization_result",
        "audio_normalization_report",
        "normalization_report",
        "audio_normalization_plan",
        "normalization_plan",
        "plan",
        "result",
        "report",
    ]

    for key in attr_keys:
        nested = _read_attr(value, key)
        if nested is not None:
            found = _extract_audio_normalization_plan_dict(nested, seen_ids)
            if found is not None:
                return found

    gathered = {
        "level_status": _read_attr(value, "level_status"),
        "audio_level_status": _read_attr(value, "audio_level_status"),
        "normalization_needed": _read_attr(value, "normalization_needed"),
        "recommended_gain_db": _read_attr(value, "recommended_gain_db"),
        "limited_gain_db": _read_attr(value, "limited_gain_db"),
        "target_rms_dbfs": _read_attr(value, "target_rms_dbfs"),
        "target_peak_dbfs": _read_attr(value, "target_peak_dbfs"),
        "reason": _read_attr(value, "reason"),
    }

    gathered = {key: item for key, item in gathered.items() if item is not None}
    if _is_plan_like(gathered):
        return _clean_plan_dict(gathered)

    return None


def _score_for_signal(level_status: str, normalization_needed: bool) -> float:
    if level_status in SCORE_BY_LEVEL_STATUS:
        return SCORE_BY_LEVEL_STATUS[level_status]

    if normalization_needed:
        return 0.7

    return 0.3


def _priority_for_score(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _signal_type_for_plan(level_status: str, normalization_needed: bool) -> str:
    if level_status in SIGNAL_TYPE_BY_LEVEL_STATUS:
        return SIGNAL_TYPE_BY_LEVEL_STATUS[level_status]

    if normalization_needed:
        return "audio_normalization_plan"

    return "audio_no_normalization_needed"


def _reason_for_signal(signal_type: str, plan: dict[str, Any]) -> str:
    custom_reason = _safe_str(plan.get("reason"), "")
    if custom_reason:
        return custom_reason

    if signal_type == "audio_gain_boost_recommended":
        return "Audio is too quiet. Gain boost is recommended."

    if signal_type == "audio_gain_reduce_recommended":
        return "Audio is too loud. Gain reduction is recommended."

    if signal_type == "audio_clipping_warning":
        return "Audio clipping was detected. Audio should be reviewed before rendering."

    if signal_type == "audio_silent_warning":
        return "Audio seems silent. Source audio should be checked."

    if signal_type == "audio_normalization_plan":
        return "Audio normalization is recommended by the normalization plan."

    if signal_type == "audio_no_normalization_needed":
        return "Audio level is acceptable. No normalization is needed."

    return "Audio normalization signal was created."


def audio_normalization_plan_to_signal(plan: Any) -> dict[str, Any] | None:
    plan_dict = extract_audio_normalization_plan_dict(plan)
    if plan_dict is None:
        return None

    level_status = _normalize_level_status(plan_dict.get("level_status"))
    normalization_needed = _safe_bool(plan_dict.get("normalization_needed"), False)

    signal_type = _signal_type_for_plan(level_status, normalization_needed)
    signal_score = _score_for_signal(level_status, normalization_needed)

    return {
        "signal_type": signal_type,
        "source": SOURCE,
        "level_status": level_status,
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "recommended_gain_db": plan_dict.get("recommended_gain_db"),
        "limited_gain_db": plan_dict.get("limited_gain_db"),
        "target_rms_dbfs": plan_dict.get("target_rms_dbfs"),
        "target_peak_dbfs": plan_dict.get("target_peak_dbfs"),
        "normalization_needed": normalization_needed,
        "signal_score": signal_score,
        "priority": _priority_for_score(signal_score),
        "reason": _reason_for_signal(signal_type, plan_dict),
        "source_plan": dict(plan_dict),
        "metadata": {
            "adapter_version": "audio-normalization-signal-adapter-v1",
            "primary_signal": True,
            "future_edit_compatible": True,
        },
    }


def _build_general_plan_signal(plan_dict: dict[str, Any]) -> dict[str, Any]:
    signal_score = 0.7

    return {
        "signal_type": "audio_normalization_plan",
        "source": SOURCE,
        "level_status": _normalize_level_status(plan_dict.get("level_status")),
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": None,
        "recommended_gain_db": plan_dict.get("recommended_gain_db"),
        "limited_gain_db": plan_dict.get("limited_gain_db"),
        "target_rms_dbfs": plan_dict.get("target_rms_dbfs"),
        "target_peak_dbfs": plan_dict.get("target_peak_dbfs"),
        "normalization_needed": True,
        "signal_score": signal_score,
        "priority": _priority_for_score(signal_score),
        "reason": _reason_for_signal("audio_normalization_plan", plan_dict),
        "source_plan": dict(plan_dict),
        "metadata": {
            "adapter_version": "audio-normalization-signal-adapter-v1",
            "primary_signal": False,
            "future_edit_compatible": True,
        },
    }


def adapt_audio_normalization_plan_to_signals(plan: Any) -> list[dict[str, Any]]:
    plan_dict = extract_audio_normalization_plan_dict(plan)
    if plan_dict is None:
        return []

    primary_signal = audio_normalization_plan_to_signal(plan_dict)
    if primary_signal is None:
        return []

    signals = [primary_signal]

    normalization_needed = _safe_bool(plan_dict.get("normalization_needed"), False)
    if normalization_needed and primary_signal.get("signal_type") != "audio_normalization_plan":
        signals.append(_build_general_plan_signal(plan_dict))

    return signals


def _count_signal_types(signals: list[dict[str, Any]]) -> dict[str, int]:
    signal_types: dict[str, int] = {}

    for signal in signals:
        signal_type = _safe_str(signal.get("signal_type"), "unknown")
        signal_types[signal_type] = signal_types.get(signal_type, 0) + 1

    return signal_types


def adapt_audio_normalization_run_report_to_signals(report: Any) -> AudioNormalizationSignalAdapterResult:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        plan_dict = extract_audio_normalization_plan_dict(report)

        if plan_dict is None:
            return AudioNormalizationSignalAdapterResult(
                status="skipped_no_normalization_plan",
                signals=[],
                signal_count=0,
                high_priority_signal_count=0,
                signal_types={},
                max_signal_score=0.0,
                avg_signal_score=0.0,
                warnings=["No audio normalization plan was found."],
                errors=[],
                recommendation="no_normalization_plan_available",
                metadata={
                    "adapter_version": "audio-normalization-signal-adapter-v1",
                    "future_edit_compatible": True,
                },
            )

        signals = adapt_audio_normalization_plan_to_signals(plan_dict)

        if not signals:
            warnings.append("Audio normalization plan was found, but no signal could be created.")

        scores = [
            _safe_float(signal.get("signal_score"), 0.0) or 0.0
            for signal in signals
        ]

        signal_count = len(signals)
        high_priority_signal_count = sum(
            1 for signal in signals if signal.get("priority") == "high"
        )

        max_signal_score = max(scores) if scores else 0.0
        avg_signal_score = sum(scores) / len(scores) if scores else 0.0

        if warnings:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            status = "ok"
            recommendation = "use_audio_edit_signals"

        return AudioNormalizationSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=signal_count,
            high_priority_signal_count=high_priority_signal_count,
            signal_types=_count_signal_types(signals),
            max_signal_score=max_signal_score,
            avg_signal_score=avg_signal_score,
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
            metadata={
                "adapter_version": "audio-normalization-signal-adapter-v1",
                "future_edit_compatible": True,
                "source_plan_found": True,
            },
        )

    except Exception as exc:
        return AudioNormalizationSignalAdapterResult(
            status="failed",
            signals=[],
            signal_count=0,
            high_priority_signal_count=0,
            signal_types={},
            max_signal_score=0.0,
            avg_signal_score=0.0,
            warnings=warnings,
            errors=[f"Audio normalization signal adapter failed safely: {exc}"],
            recommendation="retry_or_fix_audio_plan",
            metadata={
                "adapter_version": "audio-normalization-signal-adapter-v1",
                "future_edit_compatible": True,
            },
        )
        
