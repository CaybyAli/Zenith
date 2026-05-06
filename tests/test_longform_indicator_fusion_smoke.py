from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.channel_cut_profile_provider import ChannelCutProfileProvider
from core.longform_timeline_builder import LongformTimelineBuilder
from models.analysis_result import AnalysisResult
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


JOB_ID = "job_longform_indicator_fusion_smoke"


def _make_job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=[],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.9,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/fusion_smoke.mp4",
    )


def _make_analysis(duration: float = 180.0) -> AnalysisResult:
    return AnalysisResult(
        job_id=JOB_ID,
        duration_seconds=duration,
        file_size_bytes=123456,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=[],
    )


def _candidate(
    cid: str,
    start: float,
    end: float,
    score: float,
    confidence: float = 0.80,
    kind: str = "action_peak",
) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=cid,
        job_id=JOB_ID,
        start_time=start,
        end_time=end,
        highlight_score=score,
        candidate_kind=kind,
        confidence=confidence,
        signal_tags=[],
        source="smoke",
        notes=[],
    )


def _ind(
    indicator_type: str,
    start: float,
    end: float,
    score: float = 0.80,
    confidence: float = 0.70,
    polarity: str = "positive",
) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ci_{indicator_type}_{int(start)}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=confidence,
        source="smoke",
        reason=f"smoke {indicator_type}",
        polarity=polarity,
        channel_scope="gaming_main",
    )


def test_longform_indicator_fusion_changes_scores() -> None:
    """
    Candidate A: higher base score but covered by dead-time indicators → penalized.
    Candidate B: lower base score but covered by action indicators → boosted.
    After fusion B's selection_score must exceed A's, or at minimum B is boosted
    and A is penalized relative to their no-fusion base scores.
    """
    builder = LongformTimelineBuilder()
    profile = ChannelCutProfileProvider().get_profile("gaming_main")

    # Candidate A: strong base score, but dead-time/silence overlaps
    cand_a = _candidate("cand_A", start=10.0, end=30.0, score=0.72)
    # Candidate B: slightly weaker base score, but flash/action overlaps
    cand_b = _candidate("cand_B", start=60.0, end=80.0, score=0.62)

    indicators = CutIndicatorResult(
        indicators=[
            # Negative indicators covering candidate A
            _ind("silence_or_dead_air", 12.0, 26.0, score=0.85, confidence=0.75, polarity="negative"),
            _ind("round_end_dead_time", 18.0, 28.0, score=0.80, confidence=0.70, polarity="negative"),
            # Positive indicators covering candidate B
            _ind("goal_or_save_like_flash", 62.0, 68.0, score=0.90, confidence=0.80, polarity="positive"),
            _ind("high_action_burst", 65.0, 78.0, score=0.85, confidence=0.75, polarity="positive"),
        ],
        engine="smoke",
    )

    # ── Build WITHOUT fusion (baseline) ─────────────────────────────────
    base_score_a, _ = builder._score_candidate_for_longform(cand_a, [])
    base_score_b, _ = builder._score_candidate_for_longform(cand_b, [])

    # ── Build WITH fusion ────────────────────────────────────────────────
    timeline = builder.build(
        job=_make_job(),
        analysis_result=_make_analysis(duration=180.0),
        highlight_candidates=[cand_a, cand_b],
        weak_zones=[],
        cut_indicator_result=indicators,
        cut_scoring_profile=profile,
    )

    assert timeline.selected_segments, "Expected at least one selected segment"

    seg_by_cid = {seg.candidate_id: seg for seg in timeline.selected_segments}

    # Both candidates should survive (base scores are solid, B is boosted above 0.45)
    assert "cand_A" in seg_by_cid, "Candidate A should be selected"
    assert "cand_B" in seg_by_cid, "Candidate B should be selected"

    score_a = seg_by_cid["cand_A"].selection_score
    score_b = seg_by_cid["cand_B"].selection_score

    # B (action) must be boosted relative to its base
    assert score_b > base_score_b, (
        f"B should be boosted: fused={score_b:.3f} base={base_score_b:.3f}"
    )
    # A (dead-time) must be penalized relative to its base
    assert score_a < base_score_a, (
        f"A should be penalized: fused={score_a:.3f} base={base_score_a:.3f}"
    )
    # After fusion B must beat A
    assert score_b > score_a, (
        f"B (action, fused={score_b:.3f}) should outrank A (dead-time, fused={score_a:.3f})"
    )

    # Timeline notes must mention indicator fusion
    assert any("Indicator fusion:" in n for n in timeline.timeline_notes), (
        "timeline_notes should contain 'Indicator fusion:' entry"
    )

    # Segment notes for B must mention indicator_fusion_delta
    b_notes = seg_by_cid["cand_B"].notes
    assert any("indicator_fusion_delta=" in n for n in b_notes), (
        "B segment notes should contain indicator_fusion_delta"
    )

    print("LONGFORM INDICATOR FUSION SMOKE TEST PASSED")
    print(f"base_A={base_score_a:.3f} → fused_A={score_a:.3f}")
    print(f"base_B={base_score_b:.3f} → fused_B={score_b:.3f}")
    print(f"timeline_score={timeline.timeline_score}")
    fusion_note = next(
        (n for n in timeline.timeline_notes if n.startswith("Indicator fusion:")), ""
    )
    print(f"fusion_note={fusion_note}")


if __name__ == "__main__":
    test_longform_indicator_fusion_changes_scores()
