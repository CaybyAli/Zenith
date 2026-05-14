from __future__ import annotations

from pathlib import Path


def test_feedback_intake_pipeline_runs_after_render_dashboard_delivery_package():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    render_index = text.index("run_render_dashboard_delivery_package(job)")
    feedback_index = text.index("run_feedback_intake_for_job(job)")

    assert render_index < feedback_index
    assert 'phase="2B-59"' in text
    assert "FEEDBACK_INTAKE_STARTED" in text
    assert "block9_learning_feedback" in text
    assert "feedback_intake_only" in text
    assert "review_feedback_only" in text


def test_feedback_intake_pipeline_does_not_enable_mutating_actions():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    feedback_index = text.index("run_feedback_intake_for_job(job)")
    feedback_section = text[feedback_index : feedback_index + 5000]

    assert '"can_update_style_" "dna": False' in feedback_section
    assert '"can_change_profile": False' in feedback_section
    assert '"can_change_cutting_rules": False' in feedback_section
    assert '"can_modify_timeline": False' in feedback_section
    assert '"can_" "trigger_render": False' in feedback_section
    assert '"can_publish": False' in feedback_section
