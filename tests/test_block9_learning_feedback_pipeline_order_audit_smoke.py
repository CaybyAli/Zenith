from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")

EXPECTED_ORDER = [
    "run_feedback_intake_for_job",
    "run_style_dna_feedback_updater_for_job",
    "run_style_dna_review_gate_for_job",
    "run_style_dna_apply_plan_for_job",
    "run_style_dna_persistence_gate_for_job",
    "run_learning_pattern_recognition_for_job",
]

EXPECTED_METADATA_TOKENS = [
    "block9_learning_feedback",
    "feedback_intake_only",
    "style_dna_update_proposal_only",
    "style_dna_review_gate_only",
    "style_dna_apply_plan_only",
    "style_dna_persistence_gate_only",
    "learning_pattern_recognition_only",
    "no_style_dna_file_write",
    "no_profile_change",
    "no_cutting_rule_activation",
    "no_timeline_modify",
    "no_render_trigger",
    "no_publish",
]


def test_block9_pipeline_runner_order_is_correct():
    text = PIPELINE_PATH.read_text(encoding="utf-8-sig")

    positions = []
    for token in EXPECTED_ORDER:
        position = text.find(token)
        assert position != -1, f"missing pipeline runner token: {token}"
        positions.append(position)

    assert positions == sorted(positions), {
        token: position for token, position in zip(EXPECTED_ORDER, positions)
    }


def test_block9_pipeline_has_required_safety_metadata():
    text = PIPELINE_PATH.read_text(encoding="utf-8-sig")

    missing = [token for token in EXPECTED_METADATA_TOKENS if token not in text]
    assert missing == []


def test_2b65_does_not_add_a_pipeline_runner():
    text = PIPELINE_PATH.read_text(encoding="utf-8-sig")

    assert "run_block9_learning_feedback_final_audit_for_job" not in text
    assert "2B-65" not in text or "Final Audit" not in text
