from __future__ import annotations

import json

from core.focus_switch_engine import FocusDecision, FocusSwitchEngine


def test_focus_decision_log_is_persisted_as_json(tmp_path) -> None:
    decisions = [
        FocusDecision(
            timestamp=0.0,
            focus_target="facecam",
            facecam_zoom=1.8,
            gameplay_zoom=1.0,
            facecam_opacity=1.0,
            reasoning="ali_voice_intensity_bruellen",
            confidence=0.95,
        ),
        FocusDecision(
            timestamp=1.0,
            focus_target="gameplay",
            facecam_zoom=1.0,
            gameplay_zoom=1.3,
            facecam_opacity=0.3,
            reasoning="friend_keyword_boah",
            confidence=0.75,
        ),
    ]

    path = FocusSwitchEngine().write_decision_log(
        decisions,
        tmp_path / "decision_log.json",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["engine"] == "focus-switch-engine-v1"
    assert payload["summary"]["decision_count"] == 2
    assert payload["summary"]["focus_counts"]["facecam"] == 1
    assert payload["focus_decisions"][1]["focus_target"] == "gameplay"
    assert payload["focus_decisions"][1]["confidence"] > 0.6
