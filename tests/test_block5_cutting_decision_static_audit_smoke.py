from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

BLOCK5_PRODUCT_FILES = {
    "2B-25": [
        ROOT / "models" / "segment_classification.py",
        ROOT / "core" / "segment_classifier.py",
        ROOT / "models" / "segment_classification_run.py",
        ROOT / "core" / "segment_classification_runner.py",
        ROOT / "core" / "segment_classification_signal_adapter.py",
    ],
    "2B-26": [
        ROOT / "models" / "murch_scoring.py",
        ROOT / "core" / "murch_scoring_system.py",
        ROOT / "models" / "murch_scoring_run.py",
        ROOT / "core" / "murch_scoring_runner.py",
        ROOT / "core" / "murch_scoring_signal_adapter.py",
    ],
    "2B-27": [
        ROOT / "models" / "cut_list.py",
        ROOT / "core" / "cut_list_generator.py",
        ROOT / "models" / "cut_list_run.py",
        ROOT / "core" / "cut_list_runner.py",
        ROOT / "core" / "cut_list_signal_adapter.py",
    ],
    "2B-28": [
        ROOT / "models" / "clip_duration.py",
        ROOT / "core" / "clip_duration_optimizer.py",
        ROOT / "models" / "clip_duration_run.py",
        ROOT / "core" / "clip_duration_runner.py",
        ROOT / "core" / "clip_duration_signal_adapter.py",
    ],
    "2B-29": [
        ROOT / "models" / "transition_decision.py",
        ROOT / "core" / "transition_decision_engine.py",
        ROOT / "models" / "transition_decision_run.py",
        ROOT / "core" / "transition_decision_runner.py",
        ROOT / "core" / "transition_decision_signal_adapter.py",
    ],
    "2B-30": [
        ROOT / "models" / "continuity_check.py",
        ROOT / "core" / "continuity_checker.py",
        ROOT / "models" / "continuity_check_run.py",
        ROOT / "core" / "continuity_check_runner.py",
        ROOT / "core" / "continuity_check_signal_adapter.py",
    ],
    "2B-31": [
        ROOT / "models" / "final_cut_list.py",
        ROOT / "core" / "cut_list_finalizer.py",
        ROOT / "models" / "final_cut_list_run.py",
        ROOT / "core" / "cut_list_finalizer_runner.py",
        ROOT / "core" / "final_cut_list_signal_adapter.py",
    ],
}

FINAL_AUDIT_TEST_FILES = [
    ROOT / "tests" / "test_segment_classification_final_audit_smoke.py",
    ROOT / "tests" / "test_murch_scoring_final_audit_smoke.py",
    ROOT / "tests" / "test_cut_list_final_audit_smoke.py",
    ROOT / "tests" / "test_clip_duration_final_audit_smoke.py",
    ROOT / "tests" / "test_transition_decision_final_audit_smoke.py",
    ROOT / "tests" / "test_continuity_check_final_audit_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_final_audit_smoke.py",
]

BLOCK5_TEST_FILES = [
    ROOT / "tests" / "test_segment_classification_signal_adapter_smoke.py",
    ROOT / "tests" / "test_segment_classification_runner_smoke.py",
    ROOT / "tests" / "test_segment_classification_registry_integration_smoke.py",
    ROOT / "tests" / "test_segment_classification_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_segment_classification_final_audit_smoke.py",
    ROOT / "tests" / "test_murch_scoring_foundation_smoke.py",
    ROOT / "tests" / "test_murch_scoring_signal_adapter_smoke.py",
    ROOT / "tests" / "test_murch_scoring_runner_smoke.py",
    ROOT / "tests" / "test_murch_scoring_registry_integration_smoke.py",
    ROOT / "tests" / "test_murch_scoring_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_murch_scoring_final_audit_smoke.py",
    ROOT / "tests" / "test_cut_list_generator_foundation_smoke.py",
    ROOT / "tests" / "test_cut_list_signal_adapter_smoke.py",
    ROOT / "tests" / "test_cut_list_runner_smoke.py",
    ROOT / "tests" / "test_cut_list_registry_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_final_audit_smoke.py",
    ROOT / "tests" / "test_clip_duration_optimizer_foundation_smoke.py",
    ROOT / "tests" / "test_clip_duration_signal_adapter_smoke.py",
    ROOT / "tests" / "test_clip_duration_runner_smoke.py",
    ROOT / "tests" / "test_clip_duration_registry_integration_smoke.py",
    ROOT / "tests" / "test_clip_duration_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_clip_duration_final_audit_smoke.py",
    ROOT / "tests" / "test_transition_decision_foundation_smoke.py",
    ROOT / "tests" / "test_transition_decision_signal_adapter_smoke.py",
    ROOT / "tests" / "test_transition_decision_runner_smoke.py",
    ROOT / "tests" / "test_transition_decision_registry_integration_smoke.py",
    ROOT / "tests" / "test_transition_decision_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_transition_decision_final_audit_smoke.py",
    ROOT / "tests" / "test_continuity_check_foundation_smoke.py",
    ROOT / "tests" / "test_continuity_check_signal_adapter_smoke.py",
    ROOT / "tests" / "test_continuity_check_runner_smoke.py",
    ROOT / "tests" / "test_continuity_check_registry_integration_smoke.py",
    ROOT / "tests" / "test_continuity_check_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_continuity_check_final_audit_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_foundation_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_signal_adapter_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_runner_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_registry_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_final_audit_smoke.py",
]

NEW_AUDIT_TEST_FILES = [
    ROOT / "tests" / "test_block5_cutting_decision_static_audit_smoke.py",
    ROOT / "tests" / "test_block5_cutting_decision_pipeline_order_audit_smoke.py",
    ROOT / "tests" / "test_block5_cutting_decision_unified_signal_audit_smoke.py",
    ROOT / "tests" / "test_block5_cutting_decision_final_safety_audit_smoke.py",
]

CENTRAL_FILES = [
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

JOB_FIELDS = [
    "segment_classification_report",
    "segment_classification_segments",
    "murch_scoring_report",
    "murch_scoring_segment_scores",
    "cut_list_report",
    "cut_list_items",
    "clip_duration_report",
    "clip_duration_recommendations",
    "transition_decision_report",
    "transition_decision_decisions",
    "continuity_check_report",
    "continuity_check_issues",
    "final_cut_list_report",
    "final_cut_list_items",
]


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_block5_static_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }


def _assert_paths_exist(paths: list[Path]) -> None:
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    assert not missing, f"Missing files: {missing}"


def _all_audited_files() -> list[Path]:
    paths: list[Path] = []
    for group in BLOCK5_PRODUCT_FILES.values():
        paths.extend(group)
    paths.extend(BLOCK5_TEST_FILES)
    paths.extend(FINAL_AUDIT_TEST_FILES)
    paths.extend(NEW_AUDIT_TEST_FILES)
    paths.extend(CENTRAL_FILES)
    return sorted(set(paths))


def test_all_2b25_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-25"])


def test_all_2b26_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-26"])


def test_all_2b27_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-27"])


def test_all_2b28_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-28"])


def test_all_2b29_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-29"])


def test_all_2b30_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-30"])


def test_all_2b31_files_exist() -> None:
    _assert_paths_exist(BLOCK5_PRODUCT_FILES["2B-31"])


def test_all_block5_final_audit_tests_exist() -> None:
    _assert_paths_exist(FINAL_AUDIT_TEST_FILES)


def test_no_missing_block5_test_files() -> None:
    _assert_paths_exist(BLOCK5_TEST_FILES + NEW_AUDIT_TEST_FILES)


def test_job_contains_all_block5_fields_and_old_jobs_load() -> None:
    job_text = (ROOT / "models" / "job.py").read_text(encoding="utf-8")
    job = Job.from_dict(_minimal_job_data())
    job_dict = job.to_dict()

    for field in JOB_FIELDS:
        assert field in job_text, field
        assert field in job_dict, field

    assert job.segment_classification_report == {}
    assert job.murch_scoring_report == {}
    assert job.cut_list_report == {}
    assert job.clip_duration_report == {}
    assert job.transition_decision_report == {}
    assert job.continuity_check_report == {}
    assert job.final_cut_list_report == {}


def test_block5_audited_files_have_no_bom() -> None:
    for path in _all_audited_files():
        assert path.exists(), path
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path


def test_new_audit_files_end_with_newline() -> None:
    for path in NEW_AUDIT_TEST_FILES:
        assert path.exists(), path
        assert path.read_bytes().endswith(b"\n"), path
