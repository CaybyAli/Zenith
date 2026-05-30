from pathlib import Path
import json


def test_reaction_signal_ground_truth_report_contract():
    path = Path("reports/reaction_signal/stufe_e_reaction_signal_report.json")
    assert path.exists(), "Run scripts/reaction_signal_probe.py before this test."

    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["stage"] == "E_calibrated_reaction_intensity_signal_validation"
    assert report["confirmed_tracks"]["ali_mic"] == 1
    assert report["confirmed_tracks"]["gameplay"] == 3
    assert report["match_tolerance_seconds"] == 1.5

    summary = report["validation_summary"]
    assert summary["high_medium_total"] == 20
    assert summary["high_medium_pass"] == 18
    assert summary["high_medium_recall"] == 0.9
    assert summary["precision_negative_total"] == 25
    assert summary["precision_negative_false_positive"] == 0
    assert summary["gameplay_honesty_pass"] is True

    assert len(report["missed_high_medium"]) == 2
    assert len(report["precision_negative_details"]) == 25
    assert all(row["pass"] for row in report["precision_negative_details"])
