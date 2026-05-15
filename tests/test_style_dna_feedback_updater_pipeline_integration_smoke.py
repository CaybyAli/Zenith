from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_style_dna_feedback_updater():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_feedback_intake_for_job" in text
    assert "run_style_dna_feedback_updater_for_job" in text
    assert text.index("run_feedback_intake_for_job") < text.index(
        "run_style_dna_feedback_updater_for_job"
    )


def test_pipeline_runs_style_dna_feedback_updater_after_feedback_intake():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    feedback_run = "feedback_intake_report = run_feedback_intake_for_job(job)"
    style_run = "run_style_dna_feedback_updater_for_job(job)"

    assert feedback_run in text
    assert style_run in text
    assert text.index(feedback_run) < text.index(style_run)

    assert 'phase="2B-60"' in text
    assert '"block": "block9_learning_feedback"' in text
    assert '"style_dna_update_proposal_only": True' in text
    assert '"style_dna_draft_only": True' in text
    assert '"no_style_dna_file_write_in_2b_60": True' in text
    assert '"no_profile_change_in_2b_60": True' in text
    assert '"no_cutting_rule_activation_in_2b_60": True' in text
    assert '"no_timeline_modify_in_2b_60": True' in text
    assert '"no_render_trigger_in_2b_60": True' in text
    assert '"no_publish_in_2b_60": True' in text
