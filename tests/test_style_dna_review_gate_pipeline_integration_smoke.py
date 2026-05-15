from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_review_gate_runner():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_style_dna_feedback_updater_for_job" in text
    assert "run_style_dna_review_gate_for_job" in text


def test_pipeline_runs_review_gate_after_style_dna_feedback_updater():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    updater_index = text.index("run_style_dna_feedback_updater_for_job(job)")
    review_index = text.index("run_style_dna_review_gate_for_job(job)")

    assert updater_index < review_index


def test_pipeline_contains_2b61_safety_metadata():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"phase": "2B-61"' in text
    assert '"block": "block9_learning_feedback"' in text
    assert '"style_dna_review_gate_only": True' in text
    assert '"human_approval_gate_only": True' in text
    assert '"no_profile_change_in_2b_61": True' in text
    assert '"no_cutting_rule_activation_in_2b_61": True' in text
    assert '"no_timeline_modify_in_2b_61": True' in text
    assert '"no_publish_in_2b_61": True' in text
