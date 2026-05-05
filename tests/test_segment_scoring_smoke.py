from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.job import Job
from core.highlight_selector import HighlightSelector
from core.longform_timeline_builder import LongformTimelineBuilder
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)

JOB_ID = "job_segment_scoring_smoke"


def _make_job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )


def _sig(
    *,
    signal_id: str,
    start_time: float,
    end_time: float,
    signal_type: str,
    strength: float = 1.0,
    confidence: float = 0.85,
    tags: list[str] | None = None,
) -> EditSignal:
    return EditSignal(
        signal_id=signal_id,
        job_id=JOB_ID,
        start_time=start_time,
        end_time=end_time,
        signal_type=signal_type,
        strength=strength,
        confidence=confidence,
        tags=tags or [],
    )


def main() -> None:
    job = _make_job()
    analysis_result = AnalysisResult(
        job_id=JOB_ID,
        duration_seconds=600.0,
        file_size_bytes=100_000_000,
        usable_for_shorts=False,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=["synthetic segment scoring test"],
    )

    # Strong highlight window t=10-18s: audio_peak + motion_peak + audio_activity
    # Expected highlight_score: 0.42+0.34+0.18+0.16(combined) = 1.10 → clamped 1.0
    strong_signals = [
        _sig(signal_id="s1", start_time=10.0, end_time=15.0, signal_type="audio_peak", confidence=0.9),
        _sig(signal_id="s2", start_time=12.0, end_time=18.0, signal_type="motion_peak", confidence=0.85),
        _sig(signal_id="s3", start_time=10.0, end_time=18.0, signal_type="audio_activity", confidence=0.8),
    ]

    # Weaker highlight window t=60-66s: audio_peak only
    # Expected highlight_score: 0.42
    weak_highlight_signals = [
        _sig(signal_id="s4", start_time=60.0, end_time=66.0, signal_type="audio_peak", strength=0.6, confidence=0.7),
    ]

    # Quiet/negative window t=100-118s: silence_zone + low_motion_zone
    # These must NOT appear in highlight_candidates — only in weak_zones
    negative_signals = [
        _sig(signal_id="s5", start_time=100.0, end_time=115.0, signal_type="silence_zone", confidence=0.9),
        _sig(signal_id="s6", start_time=102.0, end_time=118.0, signal_type="low_motion_zone", confidence=0.85),
    ]

    all_signals = strong_signals + weak_highlight_signals + negative_signals

    # ── HIGHLIGHT SELECTOR ──────────────────────────────────────────────────
    selector = HighlightSelector()
    result = selector.select(job, analysis_result, all_signals)

    highlight_candidates = result["highlight_candidates"]
    weak_zones = result["weak_zones"]
    summary = result["summary"]

    # 1. Positive signals produce highlight candidates
    assert len(highlight_candidates) >= 1, (
        f"Expected at least 1 highlight candidate, got {len(highlight_candidates)}"
    )

    # 2. Negative signals produce weak zones (silence/low_motion)
    assert len(weak_zones) >= 1, f"Expected at least 1 weak zone, got {len(weak_zones)}"

    # 3. Summary counts are consistent
    assert summary["highlight_candidates"] == len(highlight_candidates)
    assert summary["weak_zones"] == len(weak_zones)

    # 4. All candidates belong to the correct job
    assert all(c.job_id == JOB_ID for c in highlight_candidates)
    assert all(z.job_id == JOB_ID for z in weak_zones)

    # 5. highlight_score values are within the valid 0–1 range
    for candidate in highlight_candidates:
        assert 0.0 <= candidate.highlight_score <= 1.0, (
            f"highlight_score {candidate.highlight_score} out of [0,1]"
        )
    for zone in weak_zones:
        assert 0.0 <= zone.highlight_score <= 1.0, (
            f"weak zone score {zone.highlight_score} out of [0,1]"
        )

    # 6. Times are valid for all candidates and weak zones
    for candidate in highlight_candidates + weak_zones:
        assert candidate.start_time >= 0.0, "start_time must be non-negative"
        assert candidate.end_time > candidate.start_time, "end_time must be after start_time"
        assert candidate.duration > 0.0, "duration must be positive"

    # 7. Combined peak (audio + motion) scores higher than audio_peak alone
    assert len(highlight_candidates) >= 2, (
        "Need at least 2 highlight candidates to compare strong vs weak signal window"
    )
    best_highlight = max(highlight_candidates, key=lambda c: c.highlight_score)
    min_highlight = min(highlight_candidates, key=lambda c: c.highlight_score)
    assert best_highlight.highlight_score > min_highlight.highlight_score, (
        f"Combined audio+motion peak ({best_highlight.highlight_score}) must score "
        f"higher than audio_peak alone ({min_highlight.highlight_score})"
    )

    # 8. The strong window produces an action_peak candidate
    action_peaks = [c for c in highlight_candidates if c.candidate_kind == "action_peak"]
    assert len(action_peaks) >= 1, "audio_peak + motion_peak must produce an action_peak candidate"

    # ── LONGFORM TIMELINE BUILDER ──────────────────────────────────────────
    builder = LongformTimelineBuilder()
    timeline = builder.build(
        job=job,
        analysis_result=analysis_result,
        highlight_candidates=highlight_candidates,
        weak_zones=weak_zones,
    )

    # 9. Timeline has selected segments
    assert len(timeline.selected_segments) >= 1, "Timeline must contain selected segments"

    # 10. timeline_score is within 0–1
    assert 0.0 <= timeline.timeline_score <= 1.0, (
        f"timeline_score {timeline.timeline_score} out of [0,1]"
    )

    # 11. Every segment has valid selection_score and valid timestamps
    for segment in timeline.selected_segments:
        assert 0.0 <= segment.selection_score <= 1.0, (
            f"selection_score {segment.selection_score} out of [0,1]"
        )
        assert segment.start_time >= 0.0, "segment start_time must be non-negative"
        assert segment.end_time > segment.start_time, "segment end_time must be after start_time"
        assert segment.duration > 0.0, "segment duration must be positive"
        assert segment.job_id == JOB_ID

    # 12. At least one segment has a non-zero selection_score (scoring is actually used)
    assert any(s.selection_score > 0.0 for s in timeline.selected_segments), (
        "At least one segment must have a non-zero selection_score"
    )

    # 13. The best-scoring highlight produces a higher selection_score segment
    #     than the weaker highlight — scoring order is preserved into the timeline
    segment_scores_by_start = sorted(
        ((s.start_time, s.selection_score) for s in timeline.selected_segments)
    )
    selection_scores = [score for _, score in segment_scores_by_start]
    assert max(selection_scores) > min(selection_scores), (
        "Timeline segment selection_scores must vary — better highlights must rank higher"
    )

    print("SEGMENT SCORING SMOKE TEST PASSED")
    print({
        "highlight_candidates": len(highlight_candidates),
        "weak_zones": len(weak_zones),
        "best_highlight_score": best_highlight.highlight_score,
        "min_highlight_score": min_highlight.highlight_score,
        "timeline_segments": len(timeline.selected_segments),
        "timeline_score": timeline.timeline_score,
        "selection_scores": selection_scores,
    })


if __name__ == "__main__":
    main()
