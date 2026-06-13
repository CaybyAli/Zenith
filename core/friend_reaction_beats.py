from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.focus_switch_engine import FocusSwitchEngine
from core.voice_intensity_analyzer import VoiceIntensity
from models.transcript_result import TranscriptSegment


FRIEND_REACTION_KEYWORDS = FocusSwitchEngine.FRIEND_REACTION_KEYWORDS


@dataclass(frozen=True)
class FriendReactionBeatConfig:
    min_call_pause_seconds: float = 0.5
    max_call_pause_seconds: float = 2.0
    max_beat_duration_seconds: float = 4.0
    intensity_window_seconds: float = 1.0
    friend_loud_min_intensity: int = int(VoiceIntensity.SCHREIEN)
    friend_loud_rms_percentile: float = 90.0
    ali_call_min_intensity: int = int(VoiceIntensity.LEISE_ERHOEHT)


@dataclass(frozen=True)
class FriendReactionBeat:
    start: float
    end: float
    beat_type: str
    evidence: dict[str, Any] = field(default_factory=dict)
    ali_context_text: str = ""
    friend_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": round(float(self.start), 3),
            "end": round(float(self.end), 3),
            "beat_type": self.beat_type,
            "evidence": dict(self.evidence),
            "ali_context_text": self.ali_context_text,
            "friend_text": self.friend_text,
        }


def build(
    segments: list[TranscriptSegment],
    ali_intensity_points: list[Any] | None = None,
    friend_intensity_points: list[Any] | None = None,
    config: FriendReactionBeatConfig | None = None,
) -> list[FriendReactionBeat]:
    config = config or FriendReactionBeatConfig()
    ali_points = list(ali_intensity_points or [])
    friend_points = list(friend_intensity_points or [])
    friend_loud_rms_threshold = _rms_dbfs_percentile(
        friend_points,
        percentile=float(config.friend_loud_rms_percentile),
    )
    clean_segments = sorted(
        [segment for segment in segments if _valid_segment(segment)],
        key=lambda segment: (float(segment.start_seconds), float(segment.end_seconds)),
    )

    beats: list[FriendReactionBeat] = []
    for index, segment in enumerate(clean_segments):
        if _speaker(segment) != "friend":
            continue

        if _segment_duration_seconds(segment) > float(config.max_beat_duration_seconds):
            continue

        keyword = _reaction_keyword(segment.text)
        loud_points = []
        if friend_loud_rms_threshold is not None:
            loud_points = _overlapping_intensity_points(
                friend_points,
                segment=segment,
                min_intensity=int(config.friend_loud_min_intensity),
                window_seconds=config.intensity_window_seconds,
                min_rms_dbfs=friend_loud_rms_threshold,
            )

        ali_segment, ali_index, gap_seconds = _owner_call_pause_context(
            clean_segments,
            friend_index=index,
            ali_intensity_points=ali_points,
            config=config,
        )
        has_call_pause = (
            ali_segment is not None
            and ali_index is not None
            and gap_seconds is not None
        )
        if not loud_points and not has_call_pause:
            continue

        beat_type = "friend_loud_reaction" if loud_points else "owner_call_pause"

        beats.append(
            _friend_reaction_beat(
                segment,
                index=index,
                beat_type=beat_type,
                keyword=keyword,
                loud_points=loud_points,
                friend_loud_rms_threshold=friend_loud_rms_threshold,
                ali_segment=ali_segment,
                ali_index=ali_index,
                gap_seconds=gap_seconds,
                config=config,
            )
        )

    return sorted(beats, key=lambda beat: (beat.start, beat.end, beat.beat_type))


def _friend_reaction_beat(
    segment: TranscriptSegment,
    *,
    index: int,
    beat_type: str,
    keyword: str | None,
    loud_points: list[Any],
    friend_loud_rms_threshold: float | None,
    ali_segment: TranscriptSegment | None,
    ali_index: int | None,
    gap_seconds: float | None,
    config: FriendReactionBeatConfig,
) -> FriendReactionBeat:
    evidence: dict[str, Any] = {
        "pattern": beat_type,
        "friend_segment_index": index,
    }
    if beat_type == "friend_loud_reaction":
        evidence.update(
            {
                "trigger": "friend_voice_intensity",
                "max_friend_intensity": _max_intensity_label(loud_points),
                "friend_loud_min_intensity": int(config.friend_loud_min_intensity),
                "friend_loud_rms_percentile": round(
                    float(config.friend_loud_rms_percentile),
                    3,
                ),
                "friend_intensity_points": [
                    _intensity_point_evidence(point) for point in loud_points
                ],
            }
        )
        if friend_loud_rms_threshold is not None:
            evidence["friend_loud_rms_dbfs_threshold"] = round(
                float(friend_loud_rms_threshold),
                3,
            )
    else:
        evidence["trigger"] = "ali_voice_intensity_call_pause"
    if keyword:
        evidence["keyword"] = keyword

    ali_context_text = ""
    if ali_segment is not None and ali_index is not None and gap_seconds is not None:
        tags = list(evidence.get("tags", []))
        if "owner_call_pause" not in tags:
            tags.append("owner_call_pause")
        evidence.update(
            {
                "tags": tags,
                "gap_seconds": round(gap_seconds, 3),
                "ali_segment_index": ali_index,
                "min_call_pause_seconds": round(float(config.min_call_pause_seconds), 3),
                "max_call_pause_seconds": round(float(config.max_call_pause_seconds), 3),
                "ali_call_min_intensity": int(config.ali_call_min_intensity),
            }
        )
        ali_context_text = _text(ali_segment)

    return FriendReactionBeat(
        start=round(float(segment.start_seconds), 3),
        end=round(float(segment.end_seconds), 3),
        beat_type=beat_type,
        evidence=evidence,
        ali_context_text=ali_context_text,
        friend_text=_text(segment),
    )


def _owner_call_pause_context(
    segments: list[TranscriptSegment],
    *,
    friend_index: int,
    ali_intensity_points: list[Any],
    config: FriendReactionBeatConfig,
) -> tuple[TranscriptSegment | None, int | None, float | None]:
    min_gap = max(0.0, float(config.min_call_pause_seconds))
    max_gap = max(min_gap, float(config.max_call_pause_seconds))
    friend_segment = segments[friend_index]
    friend_start = float(friend_segment.start_seconds)

    for index in range(friend_index - 1, -1, -1):
        candidate = segments[index]
        candidate_end = float(candidate.end_seconds)
        if candidate_end > friend_start:
            continue

        gap_seconds = round(friend_start - candidate_end, 3)
        if gap_seconds > max_gap:
            break

        if _speaker(candidate) != "ali":
            continue

        if not _overlapping_intensity_points(
            ali_intensity_points,
            segment=candidate,
            min_intensity=int(config.ali_call_min_intensity),
            window_seconds=config.intensity_window_seconds,
        ):
            continue

        if gap_seconds < min_gap:
            continue

        if not _has_true_silence_gap(
            segments,
            ali_index=index,
            friend_index=friend_index,
            gap_start=candidate_end,
            gap_end=friend_start,
        ):
            return None, None, None

        return candidate, index, gap_seconds

    return None, None, None


def _overlapping_intensity_points(
    points: list[Any],
    *,
    segment: TranscriptSegment,
    min_intensity: int,
    window_seconds: float,
    min_rms_dbfs: float | None = None,
) -> list[Any]:
    start = float(segment.start_seconds)
    end = float(segment.end_seconds)
    duration = max(0.001, float(window_seconds or 1.0))
    matches = []
    for point in points:
        point_start = _point_timestamp(point)
        point_end = point_start + duration
        point_rms_dbfs = _point_rms_dbfs(point)
        if (
            point_start < end
            and point_end > start
            and _point_intensity(point) >= min_intensity
            and (
                min_rms_dbfs is None
                or (
                    point_rms_dbfs is not None
                    and point_rms_dbfs >= min_rms_dbfs
                )
            )
        ):
            matches.append(point)
    return sorted(matches, key=_point_timestamp)


def _rms_dbfs_percentile(points: list[Any], *, percentile: float) -> float | None:
    values = sorted(
        value for point in points if (value := _point_rms_dbfs(point)) is not None
    )
    if not values:
        return None

    pct = _normalized_percentile(percentile)
    if len(values) == 1:
        return values[0]

    rank = (len(values) - 1) * pct
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(values) - 1)
    fraction = rank - lower_index
    lower_value = values[lower_index]
    upper_value = values[upper_index]
    return lower_value + ((upper_value - lower_value) * fraction)


def _normalized_percentile(percentile: float) -> float:
    pct = float(percentile)
    if pct > 1.0:
        pct /= 100.0
    return min(1.0, max(0.0, pct))


def _point_timestamp(point: Any) -> float:
    raw = point.get("timestamp") if isinstance(point, dict) else getattr(point, "timestamp", 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _point_intensity(point: Any) -> int:
    raw = point.get("intensity") if isinstance(point, dict) else getattr(point, "intensity", 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _point_rms_dbfs(point: Any) -> float | None:
    raw = point.get("rms_dbfs") if isinstance(point, dict) else getattr(point, "rms_dbfs", None)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def _point_intensity_label(point: Any) -> str:
    raw_label = (
        point.get("intensity_label")
        if isinstance(point, dict)
        else getattr(getattr(point, "intensity", None), "label", None)
    )
    if raw_label:
        return str(raw_label)
    try:
        return VoiceIntensity(_point_intensity(point)).label
    except ValueError:
        return str(_point_intensity(point))


def _max_intensity_label(points: list[Any]) -> str:
    if not points:
        return "unknown"
    return _point_intensity_label(max(points, key=_point_intensity))


def _intensity_point_evidence(point: Any) -> dict[str, Any]:
    data = {
        "timestamp": round(_point_timestamp(point), 3),
        "intensity": _point_intensity(point),
        "intensity_label": _point_intensity_label(point),
    }
    for field_name in ("lufs", "rms_dbfs", "speaker"):
        value = (
            point.get(field_name)
            if isinstance(point, dict)
            else getattr(point, field_name, None)
        )
        if value is not None:
            data[field_name] = value
    return data


def _has_true_silence_gap(
    segments: list[TranscriptSegment],
    *,
    ali_index: int,
    friend_index: int,
    gap_start: float,
    gap_end: float,
) -> bool:
    for index, segment in enumerate(segments):
        if index in (ali_index, friend_index):
            continue

        start = float(segment.start_seconds)
        end = float(segment.end_seconds)
        if start < gap_end and end > gap_start:
            return False

    return True


def _reaction_keyword(text: str) -> str | None:
    clean = str(text or "").lower()
    tokens = set(re.findall(r"[\w\u00c0-\u024f]+", clean, flags=re.UNICODE))
    for keyword in sorted(FRIEND_REACTION_KEYWORDS, key=len, reverse=True):
        low = str(keyword).lower()
        if len(low) <= 3:
            if low in tokens:
                return low
        elif low in clean or low in tokens:
            return low
    return None


def _valid_segment(segment: TranscriptSegment) -> bool:
    try:
        return float(segment.end_seconds) > float(segment.start_seconds)
    except (TypeError, ValueError):
        return False


def _segment_duration_seconds(segment: TranscriptSegment) -> float:
    return max(0.0, float(segment.end_seconds) - float(segment.start_seconds))


def _speaker(segment: TranscriptSegment) -> str:
    return str(getattr(segment, "speaker", "") or "").strip().lower()


def _text(segment: TranscriptSegment) -> str:
    return str(getattr(segment, "text", "") or "").strip()
