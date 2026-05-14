from __future__ import annotations

from pathlib import Path


AUDIT_FILES = [
    "tests/test_block7_story_pacing_static_audit_smoke.py",
    "tests/test_block7_story_pacing_pipeline_order_audit_smoke.py",
    "tests/test_block7_story_pacing_safety_contract_audit_smoke.py",
    "tests/test_block7_story_pacing_registry_audit_smoke.py",
    "tests/test_block7_story_pacing_job_fields_audit_smoke.py",
    "tests/test_block7_story_pacing_final_audit_smoke.py",
]

BLOCK7_PRODUCT_FILES = [
    "models/hook_identification.py",
    "core/hook_identification_engine.py",
    "core/hook_identification_runner.py",
    "core/hook_identification_signal_adapter.py",
    "models/emotional_arc.py",
    "core/emotional_arc_builder.py",
    "core/emotional_arc_runner.py",
    "core/emotional_arc_signal_adapter.py",
    "models/dynamic_pacing.py",
    "core/dynamic_pacing_engine.py",
    "core/dynamic_pacing_runner.py",
    "core/dynamic_pacing_signal_adapter.py",
    "models/pattern_interrupt.py",
    "core/pattern_interrupt_engine.py",
    "core/pattern_interrupt_runner.py",
    "core/pattern_interrupt_signal_adapter.py",
    "models/reaction_shot_placement.py",
    "core/reaction_shot_placement_engine.py",
    "core/reaction_shot_placement_runner.py",
    "core/reaction_shot_placement_signal_adapter.py",
    "models/but_therefore_story.py",
    "core/but_therefore_story_engine.py",
    "core/but_therefore_story_runner.py",
    "core/but_therefore_story_signal_adapter.py",
    "models/final_quality_validator.py",
    "core/final_quality_validator.py",
    "core/final_quality_validator_runner.py",
    "core/final_quality_validator_signal_adapter.py",
]

PIPELINE_ORDER_MARKERS = [
    "run_hook_identification_for_job",
    "run_emotional_arc_builder_for_job",
    "run_dynamic_pacing_for_job",
    "run_pattern_interrupt_for_job",
    "run_reaction_shot_placement_for_job",
    "run_but_therefore_story_for_job",
    "run_final_quality_validator",
]

SAFETY_CASE_MARKERS = [
    "test_case_a_good_block7_inputs_are_ready_or_ready_with_warnings_and_never_executable",
    "test_case_b_missing_hook_warns_but_does_not_auto_apply_hook",
    "test_case_c_block6_safety_blocked_blocks_final_quality",
    "test_case_d_monotone_dynamic_pacing_warns_but_does_not_apply_pacing_fix",
    "test_case_e_reaction_placeholder_warns_but_does_not_insert_reaction",
    "test_case_f_weak_but_therefore_ratio_warns_but_does_not_remove_and_moments",
    "test_case_g_any_can_render_true_blocks_and_output_can_render_stays_false",
    "test_case_h_any_execution_flag_true_blocks_and_output_execution_flags_stay_false",
]

REGISTRY_SOURCE_MARKERS = [
    "hook_identification",
    "emotional_arc",
    "dynamic_pacing",
    "pattern_interrupt",
    "reaction_shot_placement",
    "but_therefore_story",
    "final_quality_validator",
]

JOB_FIELD_MARKERS = [
    "hook_identification_report",
    "hook_can_render",
    "emotional_arc_report",
    "emotional_arc_can_render",
    "dynamic_pacing_report",
    "dynamic_pacing_can_render",
    "pattern_interrupt_report",
    "pattern_interrupt_can_render",
    "reaction_shot_placement_report",
    "reaction_shot_can_render",
    "but_therefore_story_report",
    "story_can_render",
    "final_quality_validation_report",
    "final_quality_can_render",
    "final_quality_can_execute_timeline",
]


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_block7_final_audit_files_exist_and_are_text_safe():
    missing = [
        path
        for path in AUDIT_FILES
        if not Path(path).is_file()
    ]

    assert missing == []

    bad_bom = []
    bad_newline = []

    for path in AUDIT_FILES:
        raw = Path(path).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad_bom.append(path)
        if raw and not raw.endswith(b"\n"):
            bad_newline.append(path)

    assert bad_bom == []
    assert bad_newline == []


def test_block7_final_audit_product_files_exist_and_are_text_safe():
    missing = [
        path
        for path in BLOCK7_PRODUCT_FILES
        if not Path(path).is_file()
    ]

    assert missing == []

    bad_bom = []
    bad_newline = []

    for path in BLOCK7_PRODUCT_FILES:
        raw = Path(path).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad_bom.append(path)
        if raw and not raw.endswith(b"\n"):
            bad_newline.append(path)

    assert bad_bom == []
    assert bad_newline == []


def test_block7_final_audit_static_safety_test_covers_forbidden_execution_surface():
    text = _read("tests/test_block7_story_pacing_static_audit_smoke.py")

    required_markers = [
        "FORBIDDEN_IMPORTS",
        "FORBIDDEN_CALL_NAMES",
        "FORBIDDEN_TEXT_PATTERNS",
        "HARD_MEDIA_PATH_PATTERNS",
        "test_block7_product_files_do_not_import_real_media_execution_libraries",
        "test_block7_product_files_do_not_call_real_media_or_timeline_execution",
        "test_block7_product_files_do_not_reference_render_or_media_paths",
        "test_block7_product_files_never_set_execution_permissions_true",
        "review_only",
        "media_unchanged",
        "can_render",
    ]

    missing = [
        marker
        for marker in required_markers
        if marker not in text
    ]

    assert missing == []


def test_block7_final_audit_pipeline_test_covers_full_story_pacing_order():
    text = _read("tests/test_block7_story_pacing_pipeline_order_audit_smoke.py")

    missing = [
        marker
        for marker in PIPELINE_ORDER_MARKERS
        if marker not in text
    ]

    assert missing == []
    assert "test_block7_pipeline_runs_story_pacing_modules_in_safe_order" in text
    assert "test_block7_pipeline_does_not_run_later_modules_before_required_inputs" in text
    assert "test_block7_pipeline_contains_review_only_safety_metadata_for_each_stage" in text


def test_block7_final_audit_safety_contract_test_covers_cases_a_to_h():
    text = _read("tests/test_block7_story_pacing_safety_contract_audit_smoke.py")

    missing = [
        marker
        for marker in SAFETY_CASE_MARKERS
        if marker not in text
    ]

    assert missing == []

    required_output_flags = [
        "can_apply_fixes",
        "can_render",
        "can_execute_timeline",
        "can_reorder_timeline",
        "can_trim",
        "can_extend",
        "can_insert_effects",
        "can_auto_apply",
    ]

    missing_flags = [
        marker
        for marker in required_output_flags
        if marker not in text
    ]

    assert missing_flags == []


def test_block7_final_audit_registry_test_covers_all_sources_and_signal_collection():
    text = _read("tests/test_block7_story_pacing_registry_audit_smoke.py")

    missing_sources = [
        marker
        for marker in REGISTRY_SOURCE_MARKERS
        if marker not in text
    ]

    assert missing_sources == []

    required_registry_tests = [
        "test_registry_contains_all_block7_sources_in_source_code",
        "test_registry_imports_all_block7_signal_adapters",
        "test_registry_collects_signals_from_all_block7_sources",
        "test_registry_collects_expected_block7_signal_types",
        "test_all_collected_block7_signals_stay_review_only_and_non_rendering",
    ]

    missing_tests = [
        marker
        for marker in required_registry_tests
        if marker not in text
    ]

    assert missing_tests == []


def test_block7_final_audit_job_fields_test_covers_from_dict_and_safe_defaults():
    text = _read("tests/test_block7_story_pacing_job_fields_audit_smoke.py")

    missing_fields = [
        marker
        for marker in JOB_FIELD_MARKERS
        if marker not in text
    ]

    assert missing_fields == []

    required_tests = [
        "test_job_model_declares_all_block7_report_and_safety_fields",
        "test_job_from_dict_loads_all_block7_report_fields",
        "test_job_defaults_keep_all_block7_render_apply_execution_flags_false",
        "test_job_from_dict_preserves_false_for_all_block7_render_apply_execution_flags",
    ]

    missing_tests = [
        marker
        for marker in required_tests
        if marker not in text
    ]

    assert missing_tests == []


def test_block7_final_audit_uses_only_tests_for_2b44_closure():
    for path in AUDIT_FILES:
        assert path.startswith("tests/")
        assert Path(path).name.startswith("test_block7_story_pacing_")
        assert Path(path).name.endswith("_smoke.py")
