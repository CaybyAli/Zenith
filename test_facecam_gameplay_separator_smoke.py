from __future__ import annotations

from core.facecam_gameplay_separator import FacecamGameplaySeparator
from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment


def main() -> None:
    separator = FacecamGameplaySeparator()

    hook_segment = TimelineSegment(
        segment_id="seg_hook",
        job_id="job_separator_smoke",
        candidate_id="cand_hook",
        start_time=5.0,
        end_time=18.0,
        segment_role="hook",
        selection_score=0.90,
        notes=[],
        source="test",
    )
    hook_candidate = HighlightCandidate(
        candidate_id="cand_hook",
        job_id="job_separator_smoke",
        start_time=5.0,
        end_time=18.0,
        highlight_score=0.88,
        candidate_kind="speech_peak",
        confidence=0.82,
        signal_tags=["intro_zone"],
        source="test",
        notes=[],
    )

    peak_segment = TimelineSegment(
        segment_id="seg_peak",
        job_id="job_separator_smoke",
        candidate_id="cand_peak",
        start_time=42.0,
        end_time=64.0,
        segment_role="peak",
        selection_score=0.94,
        notes=[],
        source="test",
    )
    peak_candidate = HighlightCandidate(
        candidate_id="cand_peak",
        job_id="job_separator_smoke",
        start_time=42.0,
        end_time=64.0,
        highlight_score=0.91,
        candidate_kind="action_peak",
        confidence=0.86,
        signal_tags=["middle_section"],
        source="test",
        notes=[],
    )

    hook_result = separator.classify_segment(hook_segment, hook_candidate)
    peak_result = separator.classify_segment(peak_segment, peak_candidate)

    assert hook_result["focus_kind"] == "facecam"
    assert peak_result["focus_kind"] == "gameplay"
    assert float(hook_result["confidence"]) >= 0.70
    assert float(peak_result["confidence"]) >= 0.80

    print("FACECAM GAMEPLAY SEPARATOR SMOKE TEST PASSED")
    print(
        {
            "hook_focus": hook_result["focus_kind"],
            "peak_focus": peak_result["focus_kind"],
            "hook_confidence": hook_result["confidence"],
            "peak_confidence": peak_result["confidence"],
        }
    )


if __name__ == "__main__":
    main()