from __future__ import annotations

import json
from pathlib import Path

from scripts.g6_2_play_segment_probe import OUTPUT_DIR, run_all_defaults


def test_g6_2_real_ground_truth_reports_pass() -> None:
    exit_code = run_all_defaults()
    assert exit_code == 0

    report_path = OUTPUT_DIR / "g6_2_play_segment_detector_report.md"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")

    assert "status: PASS" in report_text
    assert "LoL active_play vs idle/menu Anteil" in report_text
    assert "active_score = 0.28*motion" in report_text

    required_labels = [
        "rocket_league",
        "fortnite",
        "league_of_legends",
        "minecraft",
    ]

    for label in required_labels:
        segment_path = OUTPUT_DIR / f"{label}_g6_2_segments.json"
        eval_path = OUTPUT_DIR / f"{label}_g6_2_ground_truth.json"

        assert segment_path.exists(), segment_path
        assert eval_path.exists(), eval_path

        segment_data = json.loads(segment_path.read_text(encoding="utf-8"))
        eval_data = json.loads(eval_path.read_text(encoding="utf-8"))

        assert segment_data["segments"], label
        assert set(segment_data["taxonomy"]) == {
            "intro_menu_lobby",
            "active_play",
            "transition_dead_time",
            "replay_break",
            "unknown",
        }
        assert set(segment_data["intensity_values"]) == {
            "low",
            "medium",
            "high",
            "unknown",
        }

        emitted_states = {segment["state"] for segment in segment_data["segments"]}
        assert emitted_states <= set(segment_data["taxonomy"])
        assert "active_play" in emitted_states or label == "rocket_league"

        for candidate_name in [
            "low_motion_high_audio_candidate",
            "low_motion_stable_scene_candidate",
            "possible_quiet_active_play_candidate",
        ]:
            assert candidate_name in segment_data["review_candidates"]

        failed_checks = [check for check in eval_data["checks"] if check["status"] != "PASS"]
        assert failed_checks == []

    lol_eval = json.loads((OUTPUT_DIR / "league_of_legends_g6_2_ground_truth.json").read_text(encoding="utf-8"))
    lol_share = lol_eval["lol_active_vs_idle_menu_share"]
    assert lol_share is not None
    assert lol_share["active_play_share"] > lol_share["idle_menu_share"]

