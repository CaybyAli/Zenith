from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_persistence_gate_runner_after_apply_plan_runner():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    apply_import = text.index(
        "from core.style_dna_apply_plan_runner import run_style_dna_apply_plan_for_job"
    )
    persistence_import = text.index("run_style_dna_persistence_gate_for_job")

    assert apply_import < persistence_import


def test_pipeline_runs_persistence_gate_after_apply_plan():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    apply_run = text.index("run_style_dna_apply_plan_for_job(job)")
    persistence_run = text.index("run_style_dna_persistence_gate_for_job(job)")

    assert apply_run < persistence_run
    assert 'phase="2B-63"' in text
    assert "STYLE_DNA_PERSISTENCE_GATE_STARTED" in text
    assert "style_dna_persistence_gate_done" in text
    assert '"no_style_" "dna_file_write_in_2b_63": True' in text
    assert '"no_backup_write_in_2b_63": True' in text
    assert '"no_profile_change_in_2b_63": True' in text
    assert '"no_cutting_rule_activation_in_2b_63": True' in text
    assert '"no_timeline_modify_in_2b_63": True' in text
    assert '"no_" "render_trigger_in_2b_63": True' in text
    assert '"no_publish_in_2b_63": True' in text
