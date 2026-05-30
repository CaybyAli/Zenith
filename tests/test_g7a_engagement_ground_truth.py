from __future__ import annotations

import json
from pathlib import Path

from scripts.g7a_engagement_probe import OUTPUT_DIR, run_all_defaults


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def test_g7a_real_probe_outputs_ground_truth_checks_pass() -> None:
    exit_code = run_all_defaults()
    assert exit_code == 0

    report_path = OUTPUT_DIR / "g7a_engagement_report.md"
    assert report_path.exists()

    all_path = OUTPUT_DIR / "g7a_engagement_all.json"
    assert all_path.exists()

    payload = json.loads(all_path.read_text(encoding="utf-8"))

    assert payload["synthetic_frozen_proof"]["status"] == "PASS"

    for label in ("rocket_league", "fortnite", "league_of_legends", "minecraft"):
        video = payload["videos"][label]
        out_path = OUTPUT_DIR / f"{label}_g7a_engagement.json"
        assert out_path.exists()

        ratios = video["ratios"]
        for key in (
            "total_active_context_seconds",
            "keep_active_seconds",
            "trimmable_low_engagement_seconds",
            "frozen_or_paused_seconds",
            "keep_active_share",
            "trimmable_low_engagement_share",
            "frozen_or_paused_share",
        ):
            assert key in ratios

    minecraft = payload["videos"]["minecraft"]
    checks = minecraft["minecraft_owner_checks"]

    assert checks["empty_low_signal_window_932_936"]["status"] == "PASS"
    assert checks["high_signal_honesty_window_966_968"]["status"] == "PASS"

    spans = minecraft["spans"]

    low_empty_hits = [
        span for span in spans
        if _overlap(span["start_seconds"], span["end_seconds"], 932.0, 936.0) > 0
    ]
    assert any(span["keep_recommendation"] == "trimmable_low_engagement" for span in low_empty_hits)

    high_signal_hits = [
        span for span in spans
        if _overlap(span["start_seconds"], span["end_seconds"], 966.0, 968.0) > 0
    ]
    assert any(span["keep_recommendation"] == "keep_active" for span in high_signal_hits)
    assert not any(span["keep_recommendation"] == "trimmable_low_engagement" for span in high_signal_hits)
