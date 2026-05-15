from pathlib import Path


REGISTRY_PATH = Path("core/unified_edit_signal_registry.py")

EXPECTED_SOURCES = {
    "SOURCE_FEEDBACK_INTAKE": "feedback_intake",
    "SOURCE_STYLE_DNA_FEEDBACK_UPDATE": "style_dna_feedback_update",
    "SOURCE_STYLE_DNA_REVIEW_GATE": "style_dna_review_gate",
    "SOURCE_STYLE_DNA_APPLY_PLAN": "style_dna_apply_plan",
    "SOURCE_STYLE_DNA_PERSISTENCE_GATE": "style_dna_persistence_gate",
    "SOURCE_LEARNING_PATTERN_RECOGNITION": "learning_pattern_recognition",
}

EXPECTED_ADAPTER_CALLS = [
    "build_feedback_intake_signals(job)",
    "build_style_dna_feedback_update_signals(job)",
    "build_style_dna_review_gate_signals(job)",
    "build_style_dna_apply_plan_signals(job)",
    "build_style_dna_persistence_gate_signals(job)",
    "build_learning_pattern_recognition_signals(job)",
]

EXPECTED_REPORT_FIELDS = [
    "feedback_intake_report",
    "style_dna_feedback_update_report",
    "style_dna_review_gate_report",
    "style_dna_apply_plan_report",
    "style_dna_persistence_gate_report",
    "learning_pattern_recognition_report",
]

EXPECTED_SIGNAL_TYPES = [
    "feedback_intake_ready",
    "style_dna_update_draft_ready",
    "style_dna_review_approved",
    "style_dna_apply_plan_ready",
    "style_dna_persistence_approved_write",
    "learning_pattern_ready",
    "style_dna_file_write_still_not_allowed",
    "style_dna_apply_still_not_allowed",
    "style_dna_profile_change_still_not_allowed",
    "style_dna_timeline_modify_still_not_allowed",
    "style_dna_render_trigger_still_not_allowed",
    "learning_pattern_style_dna_update_still_not_allowed",
]


SIGNAL_ADAPTER_FILES = [
    Path("core/feedback_intake_signal_adapter.py"),
    Path("core/style_dna_feedback_updater_signal_adapter.py"),
    Path("core/style_dna_review_gate_signal_adapter.py"),
    Path("core/style_dna_apply_plan_signal_adapter.py"),
    Path("core/style_dna_persistence_gate_signal_adapter.py"),
    Path("core/learning_pattern_recognition_signal_adapter.py"),
]


def test_registry_has_all_block9_signal_sources():
    text = REGISTRY_PATH.read_text(encoding="utf-8-sig")

    missing = []
    for constant_name, source_value in EXPECTED_SOURCES.items():
        if constant_name not in text:
            missing.append(constant_name)
        if source_value not in text:
            missing.append(source_value)

    assert missing == []


def test_registry_collects_all_block9_report_fields():
    text = REGISTRY_PATH.read_text(encoding="utf-8-sig")

    missing = [field for field in EXPECTED_REPORT_FIELDS if field not in text]
    assert missing == []


def test_registry_calls_all_block9_signal_adapters():
    text = REGISTRY_PATH.read_text(encoding="utf-8-sig")

    missing = [call for call in EXPECTED_ADAPTER_CALLS if call not in text]
    assert missing == []


def test_block9_signal_adapters_contain_required_signal_types():
    import ast

    combined_source_text = "\n".join(
        path.read_text(encoding="utf-8-sig") for path in SIGNAL_ADAPTER_FILES
    )

    string_literals = []
    for adapter_path in SIGNAL_ADAPTER_FILES:
        tree = ast.parse(adapter_path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_literals.append(node.value)

    combined_evidence_text = combined_source_text + "\n" + "\n".join(string_literals)

    missing = [
        signal_type
        for signal_type in EXPECTED_SIGNAL_TYPES
        if signal_type not in combined_evidence_text
    ]
    assert missing == []

    assert "feedback_style_dna_update_still_not_allowed" in combined_evidence_text

def test_registry_counts_block9_sources():
    text = REGISTRY_PATH.read_text(encoding="utf-8-sig")

    for constant_name in EXPECTED_SOURCES:
        assert f"source_counts[{constant_name}]" in text
