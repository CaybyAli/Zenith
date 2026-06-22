from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "blockd_render_proof_a2.py"
    spec = importlib.util.spec_from_file_location("blockd_render_proof_a2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_filtered_candidates_and_cluster_are_artifact_driven():
    module = _load_module()
    report = {
        "candidates": [
            {
                "candidate_index": 0,
                "start": 10.0,
                "end": 10.8,
                "zoom_start": 10.1,
                "zoom_end": 10.7,
                "zoom_mode": "instant",
                "is_real_reaction": True,
                "confidence": 0.91,
                "friend_text": "A",
            },
            {
                "candidate_index": 1,
                "start": 11.0,
                "end": 11.6,
                "zoom_start": 11.0,
                "zoom_end": 11.5,
                "zoom_mode": "smooth",
                "is_real_reaction": True,
                "confidence": 0.87,
                "friend_text": "B",
            },
            {
                "candidate_index": 2,
                "start": 30.0,
                "end": 31.0,
                "zoom_start": 30.1,
                "zoom_end": 30.9,
                "zoom_mode": "smooth",
                "is_real_reaction": True,
                "confidence": 0.79,
                "friend_text": "below floor",
            },
            {
                "candidate_index": 3,
                "start": 50.0,
                "end": 50.5,
                "zoom_start": 50.0,
                "zoom_end": 50.4,
                "zoom_mode": "instant",
                "is_real_reaction": False,
                "confidence": 0.99,
                "friend_text": "not real",
            },
        ]
    }

    filtered, below_floor, counters = module._filtered_candidates(report)
    cluster = module._densest_cluster(filtered)
    planned = module._planned_cut_segments(cluster["picks"])

    assert [row["candidate_index"] for row in filtered] == [0, 1]
    assert [row["candidate_index"] for row in below_floor] == [2]
    assert counters["excluded_not_real_reaction"] == 1
    assert counters["excluded_real_below_confidence_floor"] == 1
    assert cluster["size"] == 2
    assert cluster["window_start"] == 6.0
    assert cluster["window_end"] == 15.6
    assert planned == [
        {
            "candidate_index": 0,
            "gameplay_crop_start": 10.1,
            "gameplay_crop_end": 10.7,
            "zoom_mode": "instant",
            "confidence": 0.91,
            "friend_text": "A",
        },
        {
            "candidate_index": 1,
            "gameplay_crop_start": 11.0,
            "gameplay_crop_end": 11.5,
            "zoom_mode": "smooth",
            "confidence": 0.87,
            "friend_text": "B",
        },
    ]
