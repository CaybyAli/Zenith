from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_apply_plan_runner():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_style_dna_review_gate_for_job" in text
    assert "run_style_dna_apply_plan_for_job" in text


def test_pipeline_runs_apply_plan_after_style_dna_review_gate():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    review_index = text.index("run_style_dna_review_gate_for_job(job)")
    apply_index = text.index("run_style_dna_apply_plan_for_job(job)")

    assert review_index < apply_index


def test_pipeline_contains_2b62_safety_metadata():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"phase": "2B-62"' in text
    assert '"block": "block9_learning_feedback"' in text
    assert '"style_dna_apply_plan_only": True' in text
    assert '"non_writing_apply_contract": True' in text
    assert '"style_dna_preview_only": True' in text
    assert '"no_profile_change_in_2b_62": True' in text
    assert '"no_cutting_rule_activation_in_2b_62": True' in text
    assert '"no_timeline_modify_in_2b_62": True' in text
    assert '"no_publish_in_2b_62": True' in text
