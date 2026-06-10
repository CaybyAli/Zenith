from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

QUIET_INTRO_THRESHOLD_SEC = 8.0
MAX_START_OFFSET_SEC = 45.0


class MusicIntroOffsetPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class MusicIntroAnalysis:
    music_path: str
    duration_sec: float
    first_usable_audio_sec: float
    quiet_intro_detected: bool
    analysis_status: str
    reason: str


@dataclass(frozen=True)
class MusicIntroOffsetDecision:
    music_path: str
    use_start_offset: bool
    start_offset_sec: float
    trim_intro: bool
    boost_intro: bool
    boost_gain_db: float
    decision_status: str
    reason: str


def _coerce_analysis(analysis: MusicIntroAnalysis | Mapping[str, Any]) -> MusicIntroAnalysis:
    if isinstance(analysis, MusicIntroAnalysis):
        return analysis
    required = (
        "music_path",
        "duration_sec",
        "first_usable_audio_sec",
        "quiet_intro_detected",
        "analysis_status",
        "reason",
    )
    missing = [field for field in required if field not in analysis]
    if missing:
        raise MusicIntroOffsetPolicyError(f"missing intro analysis fields: {', '.join(missing)}")
    return MusicIntroAnalysis(
        music_path=str(analysis["music_path"]),
        duration_sec=float(analysis["duration_sec"]),
        first_usable_audio_sec=float(analysis["first_usable_audio_sec"]),
        quiet_intro_detected=bool(analysis["quiet_intro_detected"]),
        analysis_status=str(analysis["analysis_status"]),
        reason=str(analysis["reason"]),
    )


def _coerce_decision(
    decision: MusicIntroOffsetDecision | Mapping[str, Any],
) -> MusicIntroOffsetDecision:
    if isinstance(decision, MusicIntroOffsetDecision):
        return decision
    required = (
        "music_path",
        "use_start_offset",
        "start_offset_sec",
        "trim_intro",
        "boost_intro",
        "boost_gain_db",
        "decision_status",
        "reason",
    )
    missing = [field for field in required if field not in decision]
    if missing:
        raise MusicIntroOffsetPolicyError(f"missing intro offset decision fields: {', '.join(missing)}")
    return MusicIntroOffsetDecision(
        music_path=str(decision["music_path"]),
        use_start_offset=bool(decision["use_start_offset"]),
        start_offset_sec=float(decision["start_offset_sec"]),
        trim_intro=bool(decision["trim_intro"]),
        boost_intro=bool(decision["boost_intro"]),
        boost_gain_db=float(decision["boost_gain_db"]),
        decision_status=str(decision["decision_status"]),
        reason=str(decision["reason"]),
    )


def validate_intro_analysis(analysis: MusicIntroAnalysis | Mapping[str, Any]) -> MusicIntroAnalysis:
    item = _coerce_analysis(analysis)
    if not item.music_path.strip():
        raise MusicIntroOffsetPolicyError("music_path is required")
    if item.duration_sec <= 0.0:
        raise MusicIntroOffsetPolicyError("duration_sec must be greater than 0")
    if item.first_usable_audio_sec < 0.0:
        raise MusicIntroOffsetPolicyError("first_usable_audio_sec must not be negative")
    if item.first_usable_audio_sec >= item.duration_sec:
        raise MusicIntroOffsetPolicyError("first_usable_audio_sec must be before duration_sec")
    if not item.analysis_status.strip():
        raise MusicIntroOffsetPolicyError("analysis_status is required")
    if not item.reason.strip():
        raise MusicIntroOffsetPolicyError("reason is required")
    return item


def build_intro_offset_decision(
    analysis: MusicIntroAnalysis | Mapping[str, Any],
) -> MusicIntroOffsetDecision:
    item = validate_intro_analysis(analysis)
    if item.first_usable_audio_sec >= QUIET_INTRO_THRESHOLD_SEC:
        start_offset = min(item.first_usable_audio_sec, MAX_START_OFFSET_SEC)
        reason_parts = ["quiet_intro_trimmed"]
        if item.first_usable_audio_sec > MAX_START_OFFSET_SEC:
            reason_parts.append("offset_clamped")
        return validate_intro_offset_decision(
            MusicIntroOffsetDecision(
                music_path=item.music_path,
                use_start_offset=True,
                start_offset_sec=start_offset,
                trim_intro=True,
                boost_intro=False,
                boost_gain_db=0.0,
                decision_status="planned",
                reason=";".join(reason_parts),
            )
        )

    return validate_intro_offset_decision(
        MusicIntroOffsetDecision(
            music_path=item.music_path,
            use_start_offset=False,
            start_offset_sec=0.0,
            trim_intro=False,
            boost_intro=False,
            boost_gain_db=0.0,
            decision_status="not_needed",
            reason="usable_audio_near_start",
        )
    )


def validate_intro_offset_decision(
    decision: MusicIntroOffsetDecision | Mapping[str, Any],
) -> MusicIntroOffsetDecision:
    item = _coerce_decision(decision)
    if not item.music_path.strip():
        raise MusicIntroOffsetPolicyError("music_path is required")
    if item.start_offset_sec < 0.0:
        raise MusicIntroOffsetPolicyError("start_offset_sec must not be negative")
    if item.start_offset_sec > MAX_START_OFFSET_SEC:
        raise MusicIntroOffsetPolicyError("start_offset_sec must not exceed max offset")
    if item.boost_intro is not False:
        raise MusicIntroOffsetPolicyError("intro boost must stay disabled")
    if item.boost_gain_db != 0.0:
        raise MusicIntroOffsetPolicyError("intro boost gain must be 0.0")
    if item.use_start_offset is False and item.start_offset_sec != 0.0:
        raise MusicIntroOffsetPolicyError("disabled offset must use 0.0 seconds")
    if item.trim_intro is True and item.use_start_offset is not True:
        raise MusicIntroOffsetPolicyError("trim_intro requires use_start_offset")
    if not item.decision_status.strip():
        raise MusicIntroOffsetPolicyError("decision_status is required")
    if not item.reason.strip():
        raise MusicIntroOffsetPolicyError("reason is required")
    return item
