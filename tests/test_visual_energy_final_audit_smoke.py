from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


VISUAL_ENERGY_FILES = [
    "models/visual_energy.py",
    "core/visual_energy_calculator.py",
    "models/visual_energy_run.py",
    "core/visual_energy_runner.py",
    "core/visual_energy_signal_adapter.py",
]

VISUAL_ENERGY_TEST_FILES = [
    "tests/test_visual_energy_foundation_smoke.py",
    "tests/test_visual_energy_runner_smoke.py",
    "tests/test_visual_energy_pipeline_integration_smoke.py",
    "tests/test_visual_energy_signal_adapter_smoke.py",
    "tests/test_visual_energy_registry_integration_smoke.py",
    "tests/test_visual_energy_final_audit_smoke.py",
]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_visual_energy_implementation_files_exist() -> None:
    for relative_path in VISUAL_ENERGY_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_all_visual_energy_test_files_exist() -> None:
    for relative_path in VISUAL_ENERGY_TEST_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_visual_energy_models_and_calculator_exist() -> None:
    model_text = _read_text("models/visual_energy.py")
    calculator_text = _read_text("core/visual_energy_calculator.py")

    assert "class VisualEnergyPoint" in model_text
    assert "class VisualEnergySegment" in model_text
    assert "class VisualEnergyResult" in model_text
    assert "def calculate_visual_energy(" in calculator_text
    assert "def calculate_visual_energy_from_job(" in calculator_text
    assert "def build_visual_energy_points(" in calculator_text
    assert "def build_visual_energy_segments(" in calculator_text
    assert "def classify_visual_energy_score(" in calculator_text


def test_visual_energy_runner_and_job_wiring_exist() -> None:
    runner_text = _read_text("core/visual_energy_runner.py")
    job_text = _read_text("models/job.py")

    assert "def run_visual_energy_for_job(" in runner_text
    assert "def apply_visual_energy_run_report_to_job(" in runner_text

    required_fields = [
        "visual_energy_report",
        "visual_energy_status",
        "visual_energy_result",
        "visual_energy_points",
        "visual_energy_segments",
        "visual_energy_point_count",
        "visual_energy_segment_count",
        "visual_energy_high_segment_count",
        "visual_energy_low_segment_count",
        "visual_energy_technical_warning_segment_count",
        "visual_energy_duration_seconds",
        "visual_energy_frame_sample_rate",
        "visual_energy_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in job_text


def test_gaming_pipeline_contains_visual_energy_block() -> None:
    text = _read_text("core/gaming_pipeline.py")

    assert "Visual Energy Score (2B-18-C)" in text
    assert "run_visual_energy_for_job(job)" in text
    assert "apply_visual_energy_run_report_to_job(job, visual_energy_report)" in text
    assert "VISUAL_ENERGY_STARTED" in text
    assert "VISUAL_ENERGY_DONE" in text
    assert "VISUAL_ENERGY_SKIPPED" in text
    assert "VISUAL_ENERGY_FAILED" in text
    assert 'step_name="visual_energy_done"' in text


def test_gaming_pipeline_visual_energy_position_is_after_screen_content() -> None:
    text = _read_text("core/gaming_pipeline.py")

    screen_content_position = text.index("Screen Content Classification (2B-17-C)")
    visual_energy_position = text.index("Visual Energy Score (2B-18-C)")
    rms_energy_position = text.index("RMS Energy")

    assert screen_content_position < visual_energy_position
    assert visual_energy_position < rms_energy_position


def test_unified_registry_imports_visual_energy_adapter() -> None:
    text = _read_text("core/unified_edit_signal_registry.py")

    assert (
        "from core.visual_energy_signal_adapter "
        "import adapt_visual_energy_report_to_signals"
    ) in text


def test_unified_registry_processes_visual_energy_source() -> None:
    text = _read_text("core/unified_edit_signal_registry.py")

    assert 'SOURCE_VISUAL_ENERGY = "visual_energy"' in text
    assert 'visual_energy_report = _job_attr(job, "visual_energy_report")' in text
    assert 'visual_energy_segments = _job_attr(job, "visual_energy_segments")' in text
    assert 'visual_energy_result = _job_attr(job, "visual_energy_result")' in text
    assert "adapt_visual_energy_report_to_signals(visual_energy_report)" in text
    assert "source_counts[SOURCE_VISUAL_ENERGY]" in text
    assert "_normalize_signal(signal, SOURCE_VISUAL_ENERGY)" in text


def test_visual_energy_signal_adapter_has_expected_signal_types() -> None:
    text = _read_text("core/visual_energy_signal_adapter.py")

    assert "visual_peak_energy_segment" in text
    assert "visual_high_energy_segment" in text
    assert "visual_low_energy_segment" in text
    assert "visual_technical_warning_segment" in text
    assert "review_visual_highlight_candidate" in text
    assert "review_visual_engagement_candidate" in text
    assert "review_possible_trim_low_visual_energy" in text
    assert "review_visual_technical_warning" in text


def test_visual_energy_has_no_automatic_cut_remove_or_highlight_decision() -> None:
    files_to_check = [
        "core/visual_energy_calculator.py",
        "core/visual_energy_runner.py",
        "core/visual_energy_signal_adapter.py",
        "core/gaming_pipeline.py",
        "core/unified_edit_signal_registry.py",
    ]

    forbidden_action_strings = [
        '"remove_now"',
        '"hard_remove"',
        '"auto_remove"',
        '"auto_highlight"',
        '"force_cut"',
        "'remove_now'",
        "'hard_remove'",
        "'auto_remove'",
        "'auto_highlight'",
        "'force_cut'",
    ]

    allowed_safety_flags = [
        '"no_auto_remove": True',
        '"no_auto_highlight": True',
        '"no_cut_decision": True',
        '"remove_now",',
        '"hard_remove",',
        '"auto_remove",',
        '"auto_highlight",',
        '"force_cut",',
    ]

    for relative_path in files_to_check:
        text = _read_text(relative_path)

        for allowed_flag in allowed_safety_flags:
            text = text.replace(allowed_flag, "")

        for forbidden_action in forbidden_action_strings:
            assert forbidden_action not in text, (
                f"{forbidden_action} found in {relative_path}"
            )


def test_final_audit_file_has_no_bom() -> None:
    content = (
        REPO_ROOT / "tests" / "test_visual_energy_final_audit_smoke.py"
    ).read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_final_audit_file_ends_with_newline() -> None:
    content = (
        REPO_ROOT / "tests" / "test_visual_energy_final_audit_smoke.py"
    ).read_bytes()

    assert content.endswith(b"\n")
