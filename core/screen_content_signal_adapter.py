from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_SCREEN_CONTENT_SEGMENTS = "skipped_no_screen_content_segments"
STATUS_FAILED = "failed"

SCREEN_TYPE_GAMEPLAY = "gameplay"
SCREEN_TYPE_MENU = "menu"
SCREEN_TYPE_LOBBY = "lobby"
SCREEN_TYPE_LOADING = "loading"
SCREEN_TYPE_SCOREBOARD = "scoreboard"
SCREEN_TYPE_DEATH_SCREEN = "death_screen"
SCREEN_TYPE_VICTORY_SCREEN = "victory_screen"
SCREEN_TYPE_BLACK_SCREEN = "black_screen"
SCREEN_TYPE_INTRO_OUTRO_CANDIDATE = "intro_outro_candidate"

SIGNAL_TYPE_GAMEPLAY = "screen_gameplay_segment"
SIGNAL_TYPE_MENU = "screen_menu_segment"
SIGNAL_TYPE_LOBBY = "screen_lobby_segment"
SIGNAL_TYPE_LOADING = "screen_loading_segment"
SIGNAL_TYPE_SCOREBOARD = "screen_scoreboard_segment"
SIGNAL_TYPE_DEATH = "screen_death_segment"
SIGNAL_TYPE_VICTORY = "screen_victory_segment"
SIGNAL_TYPE_BLACK = "screen_black_segment"
SIGNAL_TYPE_INTRO_OUTRO = "screen_intro_outro_candidate"

SOURCE_SCREEN_CONTENT = "screen_content"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _extract_screen_content_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    for key in ("screen_content_segments", "segments"):
        raw_segments = source_dict.get(key)
        if isinstance(raw_segments, list):
            return [dict(item) for item in raw_segments if isinstance(item, dict)]

    screen_content_report = source_dict.get("screen_content_report")
    if isinstance(screen_content_report, dict):
        report_segments = _extract_screen_content_segments(screen_content_report)
        if report_segments:
            return report_segments

    screen_content_result = source_dict.get("screen_content_result")
    if isinstance(screen_content_result, dict):
        result_segments = _extract_screen_content_segments(screen_content_result)
        if result_segments:
            return result_segments

    for attr_name in (
        "screen_content_segments",
        "segments",
        "screen_content_report",
        "screen_content_result",
    ):
        raw_value = getattr(source, attr_name, None)

        if isinstance(raw_value, list):
            result: list[dict[str, Any]] = []
            for item in raw_value:
                item_dict = _safe_dict(item)
                if item_dict:
                    result.append(item_dict)
            if result:
                return result

        raw_dict = _safe_dict(raw_value)
        if raw_dict:
            nested_segments = _extract_screen_content_segments(raw_dict)
            if nested_segments:
                return nested_segments

    return []


def _mapping_for_screen_type(screen_type: str) -> dict[str, str] | None:
    if screen_type == SCREEN_TYPE_GAMEPLAY:
        return {
            "signal_type": SIGNAL_TYPE_GAMEPLAY,
            "action_hint": "keep_content_context",
            "priority": "medium",
            "reason": "gameplay_screen_detected",
        }

    if screen_type == SCREEN_TYPE_MENU:
        return {
            "signal_type": SIGNAL_TYPE_MENU,
            "action_hint": "review_possible_trim_menu",
            "priority": "medium",
            "reason": "menu_screen_detected",
        }

    if screen_type == SCREEN_TYPE_LOBBY:
        return {
            "signal_type": SIGNAL_TYPE_LOBBY,
            "action_hint": "review_possible_trim_lobby",
            "priority": "medium",
            "reason": "lobby_screen_detected",
        }

    if screen_type == SCREEN_TYPE_LOADING:
        return {
            "signal_type": SIGNAL_TYPE_LOADING,
            "action_hint": "review_possible_trim_loading",
            "priority": "high",
            "reason": "loading_screen_detected",
        }

    if screen_type == SCREEN_TYPE_SCOREBOARD:
        return {
            "signal_type": SIGNAL_TYPE_SCOREBOARD,
            "action_hint": "review_scoreboard_context",
            "priority": "medium",
            "reason": "scoreboard_screen_detected",
        }

    if screen_type == SCREEN_TYPE_DEATH_SCREEN:
        return {
            "signal_type": SIGNAL_TYPE_DEATH,
            "action_hint": "review_death_context",
            "priority": "medium",
            "reason": "death_screen_detected",
        }

    if screen_type == SCREEN_TYPE_VICTORY_SCREEN:
        return {
            "signal_type": SIGNAL_TYPE_VICTORY,
            "action_hint": "keep_or_highlight_victory",
            "priority": "high",
            "reason": "victory_screen_detected",
        }

    if screen_type == SCREEN_TYPE_BLACK_SCREEN:
        return {
            "signal_type": SIGNAL_TYPE_BLACK,
            "action_hint": "review_possible_trim_black_screen",
            "priority": "high",
            "reason": "black_screen_detected",
        }

    if screen_type == SCREEN_TYPE_INTRO_OUTRO_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_INTRO_OUTRO,
            "action_hint": "review_intro_outro_boundary",
            "priority": "medium",
            "reason": "intro_outro_candidate_detected",
        }

    return None


def build_screen_content_signal(
    screen_content_segment: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any] | None:
    screen_type = _safe_string(screen_content_segment.get("screen_type"), "")
    mapping = _mapping_for_screen_type(screen_type)
    if mapping is None:
        return None

    start_seconds = max(0.0, _safe_float(screen_content_segment.get("start_seconds"), 0.0))
    end_seconds = max(
        start_seconds,
        _safe_float(screen_content_segment.get("end_seconds"), start_seconds),
    )

    duration_seconds = _safe_float(
        screen_content_segment.get("duration_seconds"),
        end_seconds - start_seconds,
    )
    duration_seconds = max(0.0, duration_seconds)

    center_seconds = start_seconds + (duration_seconds / 2.0)
    if end_seconds > start_seconds:
        center_seconds = start_seconds + ((end_seconds - start_seconds) / 2.0)

    avg_confidence = _clamp_score(screen_content_segment.get("avg_confidence"), 0.0)
    max_confidence = _clamp_score(
        screen_content_segment.get("max_confidence"),
        avg_confidence,
    )
    signal_score = avg_confidence
    confidence = _clamp_score(screen_content_segment.get("confidence"), max_confidence)
    signal_type = mapping["signal_type"]

    return {
        "signal_id": (
            f"screen_content_{source_index}_{signal_type}_"
            f"{start_seconds:.3f}_{end_seconds:.3f}"
        ),
        "signal_type": signal_type,
        "source": SOURCE_SCREEN_CONTENT,
        "start_seconds": round(start_seconds, 6),
        "end_seconds": round(end_seconds, 6),
        "center_seconds": round(center_seconds, 6),
        "duration_seconds": round(duration_seconds, 6),
        "signal_score": signal_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": {
            "original_screen_type": screen_type,
            "avg_confidence": avg_confidence,
            "max_confidence": max_confidence,
            "point_count": _safe_int(screen_content_segment.get("point_count"), 0),
            "recommendation": _safe_string(
                screen_content_segment.get("recommendation"),
                "",
            ),
            "source_index": source_index,
            "warnings": _safe_list(screen_content_segment.get("warnings")),
            "errors": _safe_list(screen_content_segment.get("errors")),
        },
    }


@dataclass
class ScreenContentSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    gameplay_signal_count: int = 0
    menu_or_lobby_signal_count: int = 0
    loading_signal_count: int = 0
    victory_signal_count: int = 0
    black_screen_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "gameplay_signal_count": self.gameplay_signal_count,
            "menu_or_lobby_signal_count": self.menu_or_lobby_signal_count,
            "loading_signal_count": self.loading_signal_count,
            "victory_signal_count": self.victory_signal_count,
            "black_screen_signal_count": self.black_screen_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ScreenContentSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            gameplay_signal_count=int(data.get("gameplay_signal_count", 0) or 0),
            menu_or_lobby_signal_count=int(
                data.get("menu_or_lobby_signal_count", 0) or 0
            ),
            loading_signal_count=int(data.get("loading_signal_count", 0) or 0),
            victory_signal_count=int(data.get("victory_signal_count", 0) or 0),
            black_screen_signal_count=int(
                data.get("black_screen_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_screen_content_segments_to_signals(
    screen_content_segments: list[Any],
) -> ScreenContentSignalAdapterResult:
    try:
        valid_segments: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(screen_content_segments):
            segment_dict = _safe_dict(segment)
            if not segment_dict:
                warnings.append(f"invalid_screen_content_segment_skipped:{index}")
                continue
            valid_segments.append(segment_dict)

        if not valid_segments:
            return ScreenContentSignalAdapterResult(
                status=STATUS_SKIPPED_NO_SCREEN_CONTENT_SEGMENTS,
                signals=[],
                signal_count=0,
                gameplay_signal_count=0,
                menu_or_lobby_signal_count=0,
                loading_signal_count=0,
                victory_signal_count=0,
                black_screen_signal_count=0,
                warnings=warnings + ["no_screen_content_segments_found"],
                errors=[],
                recommendation="provide_screen_content_segments",
            )

        signals: list[dict[str, Any]] = []
        for index, segment in enumerate(valid_segments):
            signal = build_screen_content_signal(segment, source_index=index)
            if signal is None:
                warnings.append(f"unsupported_screen_type_skipped:{index}")
                continue
            signals.append(signal)

        if not signals:
            return ScreenContentSignalAdapterResult(
                status=STATUS_SKIPPED_NO_SCREEN_CONTENT_SEGMENTS,
                signals=[],
                signal_count=0,
                gameplay_signal_count=0,
                menu_or_lobby_signal_count=0,
                loading_signal_count=0,
                victory_signal_count=0,
                black_screen_signal_count=0,
                warnings=warnings + ["no_supported_screen_content_segments_found"],
                errors=[],
                recommendation="provide_screen_content_segments",
            )

        gameplay_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_GAMEPLAY
        )
        menu_or_lobby_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") in {SIGNAL_TYPE_MENU, SIGNAL_TYPE_LOBBY}
        )
        loading_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_LOADING
        )
        victory_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_VICTORY
        )
        black_screen_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_BLACK
        )

        status = STATUS_OK
        if warnings:
            status = STATUS_COMPLETED_WITH_WARNINGS

        recommendation = "review_screen_content_signals"
        if loading_signal_count > 0:
            recommendation = "review_loading_screen_segments"
        if black_screen_signal_count > 0:
            recommendation = "review_black_screen_segments"
        if victory_signal_count > 0:
            recommendation = "keep_or_highlight_victory_segments"

        return ScreenContentSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            gameplay_signal_count=gameplay_signal_count,
            menu_or_lobby_signal_count=menu_or_lobby_signal_count,
            loading_signal_count=loading_signal_count,
            victory_signal_count=victory_signal_count,
            black_screen_signal_count=black_screen_signal_count,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
        )

    except Exception as exc:
        return ScreenContentSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            gameplay_signal_count=0,
            menu_or_lobby_signal_count=0,
            loading_signal_count=0,
            victory_signal_count=0,
            black_screen_signal_count=0,
            warnings=[],
            errors=[f"screen_content_signal_adapter_failed: {exc}"],
            recommendation="review_screen_content_signal_adapter_error",
        )


def adapt_screen_content_report_to_signals(
    screen_content_report: Any,
) -> ScreenContentSignalAdapterResult:
    try:
        screen_content_segments = _extract_screen_content_segments(screen_content_report)

        return adapt_screen_content_segments_to_signals(screen_content_segments)

    except Exception as exc:
        return ScreenContentSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            gameplay_signal_count=0,
            menu_or_lobby_signal_count=0,
            loading_signal_count=0,
            victory_signal_count=0,
            black_screen_signal_count=0,
            warnings=[],
            errors=[f"screen_content_report_signal_adapter_failed: {exc}"],
            recommendation="review_screen_content_signal_adapter_error",
        )
