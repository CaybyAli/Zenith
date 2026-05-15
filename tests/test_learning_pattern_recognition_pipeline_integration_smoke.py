from pathlib import Path


def test_learning_pattern_pipeline_runs_after_style_dna_persistence_gate():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    persistence_index = text.index("run_style_dna_persistence_gate_for_job(job)")
    learning_index = text.index("run_learning_pattern_recognition_for_job(job)")

    assert persistence_index < learning_index
    assert "phase=\"2B-64\"" in text
    assert "LEARNING_PATTERN_RECOGNITION_STARTED" in text
    assert "learning_pattern_recognition_done" in text
    assert "learning_pattern_recognition_only" in text
    assert "feedback_trend_analysis_only" in text
    assert '"no_style_" "dna_file_write_in_2b_64"' in text
    assert '"no_profile_change_in_2b_64"' in text
    assert '"no_cutting_rule_activation_in_2b_64"' in text
    assert '"no_timeline_modify_in_2b_64"' in text
    assert '"no_" "render_trigger_in_2b_64"' in text
    assert '"no_publish_in_2b_64"' in text
