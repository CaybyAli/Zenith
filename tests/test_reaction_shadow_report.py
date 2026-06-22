from __future__ import annotations

from core.reaction_shadow_report import build_a2_reaction_candidates, build_shadow_report


def test_build_a2_reaction_candidates_keeps_enumerate_source_index() -> None:
    segments = [
        {"start": 0.0, "end": 1.0, "text": "alpha", "speaker": "unknown"},
        {"start": 2.0, "end": 3.0, "text": "bravo", "speaker": "unknown"},
        {"start": 4.0, "end": 5.0, "text": "charlie", "speaker": "unknown"},
    ]

    candidates = build_a2_reaction_candidates(segments)

    assert [row["source_index"] for row in candidates] == [0, 1, 2]
    assert candidates[1]["friend_text"] == "bravo"
    assert candidates[1]["beat_type"] == "a2_segment"


def test_build_shadow_report_joins_selections_by_accepted_position() -> None:
    accepted = [
        {
            "source_index": 8,
            "start": 10.0,
            "end": 11.0,
            "friend_text": "first accepted",
            "zoom_start": 9.95,
            "zoom_end": 11.05,
            "zoom_mode": "instant",
        },
        {
            "source_index": 12,
            "start": 20.0,
            "end": 21.0,
            "friend_text": "second accepted",
            "zoom_start": 19.95,
            "zoom_end": 21.05,
            "zoom_mode": "smooth",
        },
    ]
    selections = [
        {
            "candidate_index": 1,
            "is_real_reaction": True,
            "confidence": 0.91,
            "reason": "real beat",
        },
        {
            "candidate_index": 0,
            "is_real_reaction": False,
            "confidence": 0.22,
            "reason": "not enough",
        },
    ]

    report = build_shadow_report(accepted, [], {}, selections, meta={"pair_id": "pair_009"})

    assert report["candidates"][0]["source_index"] == 8
    assert report["candidates"][0]["is_real_reaction"] is False
    assert report["candidates"][0]["reason"] == "not enough"
    assert report["candidates"][1]["source_index"] == 12
    assert report["candidates"][1]["is_real_reaction"] is True
    assert report["candidates"][1]["confidence"] == 0.91


def test_build_shadow_report_selected_count_filters_is_real_reaction() -> None:
    accepted = [
        {"source_index": 0, "start": 1.0, "end": 2.0, "friend_text": "one"},
        {"source_index": 1, "start": 3.0, "end": 4.0, "friend_text": "two"},
        {"source_index": 2, "start": 5.0, "end": 6.0, "friend_text": "three"},
    ]
    selections = [
        {"candidate_index": 0, "is_real_reaction": True, "confidence": 0.8, "reason": "yes"},
        {"candidate_index": 1, "is_real_reaction": False, "confidence": 0.7, "reason": "no"},
        {"candidate_index": 2, "is_real_reaction": True, "confidence": 0.6, "reason": "yes"},
    ]

    report = build_shadow_report(accepted, [], {}, selections, meta={})

    assert report["summary"] == {
        "candidate_count": 3,
        "accepted_count": 3,
        "selected_count": 2,
    }


def test_build_shadow_report_passes_rejected_by_presence_through() -> None:
    rejected = [
        {
            "source_index": 4,
            "start": 7.0,
            "end": 8.0,
            "friend_text": "silent",
            "rejected_reason": "rejected_silence",
        }
    ]

    report = build_shadow_report([], rejected, {"accepted_count": 0}, [], meta={})

    assert report["rejected_by_presence"] == rejected
    assert report["summary"]["candidate_count"] == 1
