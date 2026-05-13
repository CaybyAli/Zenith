from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "final_cut_list.py",
    ROOT / "core" / "cut_list_finalizer.py",
    ROOT / "models" / "final_cut_list_run.py",
    ROOT / "core" / "cut_list_finalizer_runner.py",
    ROOT / "core" / "final_cut_list_signal_adapter.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_cut_list_finalizer_foundation_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_runner_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_signal_adapter_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_registry_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_finalizer_final_audit_smoke.py",
]

PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
REGISTRY_FILE = ROOT / "core" / "unified_edit_signal_registry.py"
JOB_FILE = ROOT / "models" / "job.py"

FORBIDDEN_STRINGS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_transition",
    "auto_fade",
    "auto_j_cut",
    "auto_l_cut",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "final_cut",
    "apply_transition",
    "apply_final_cutlist",
    "execute_final_cutlist",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_block() -> str:
    text = _read(PIPELINE_FILE)
    start = text.index("# -- Cut List Finalization (2B-31-C)")
    end = text.index("# -- End Cut List Finalization", start)
    return text[start:end]


def _scrub_allowed_required_names(text: str) -> str:
    allowed = [
        "apply_cut_list_finalization_run_report_to_job",
        "final_cut_list",
        "FINAL_CUT_LIST",
        "FinalCutList",
        "FINAL_KEEP_REVIEW",
        "FINAL_KEEP_HIGH_VALUE",
        "FINAL_TRIM_REVIEW",
        "FINAL_REMOVE_REVIEW",
        "FINAL_PROTECT",
        "FINAL_CENSOR_KEEP",
        "FINAL_TECHNICAL_REVIEW",
        "FINAL_BLOCKED_BY_CONTINUITY",
        "FINAL_UNKNOWN_REVIEW",
        "review_final_remove_candidate",
        "review_final_trim_candidate",
        "protect_final_cutlist_segment",
        "preserve_final_segment_for_censor_sfx",
        "block_final_cutlist_until_review",
    ]
    scrubbed = text
    for value in allowed:
        scrubbed = scrubbed.replace(value, "")
        scrubbed = scrubbed.replace(value.lower(), "")
    return scrubbed


def test_all_2b31_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), path


def test_all_2b31_tests_exist():
    for path in TEST_FILES:
        assert path.exists(), path


def test_job_final_cut_list_fields_exist_and_old_jobs_load():
    data = {
        "job_id": "job_final_cut_list_audit",
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
    job = Job.from_dict(data)
    job_dict = job.to_dict()

    expected_fields = [
        "final_cut_list_report",
        "final_cut_list_status",
        "final_cut_list_items",
        "final_cut_list_item_count",
        "final_cut_list_keep_review_count",
        "final_cut_list_keep_high_value_count",
        "final_cut_list_trim_review_count",
        "final_cut_list_remove_review_count",
        "final_cut_list_protect_count",
        "final_cut_list_censor_keep_count",
        "final_cut_list_technical_review_count",
        "final_cut_list_blocked_by_continuity_count",
        "final_cut_list_unknown_review_count",
        "final_cut_list_review_required_count",
        "final_cut_list_blocking_issue_count",
        "final_cut_list_recommendation",
    ]

    for field in expected_fields:
        assert field in job_dict

    assert job.final_cut_list_report == {}
    assert job.final_cut_list_items == []
    assert job.final_cut_list_recommendation is None


def test_pipeline_contains_cut_list_finalization_block_after_continuity():
    text = _read(PIPELINE_FILE)
    block = _pipeline_block()

    assert "from core.cut_list_finalizer_runner import (" in text
    assert "run_cut_list_finalization_for_job" in text
    assert "apply_cut_list_finalization_run_report_to_job" in text
    assert "CUT_LIST_FINALIZATION_STARTED" in block
    assert "CUT_LIST_FINALIZATION_DONE" in block
    assert "CUT_LIST_FINALIZATION_SKIPPED" in block
    assert "CUT_LIST_FINALIZATION_FAILED" in block
    assert 'step_name="cut_list_finalization_done"' in block
    assert text.index("# -- Cut List Finalization (2B-31-C)") > text.index(
        "# -- Continuity Check (2B-30-C)"
    )


def test_registry_imports_and_processes_cut_list_finalizer():
    text = _read(REGISTRY_FILE)

    assert "adapt_final_cut_list_report_to_signals" in text
    assert 'SOURCE_CUT_LIST_FINALIZER = "cut_list_finalizer"' in text
    assert "final_cut_list_report" in text
    assert "final_cut_list_items" in text
    assert "source_counts[SOURCE_CUT_LIST_FINALIZER]" in text


def test_product_files_do_not_contain_forbidden_execution_strings():
    for path in PRODUCT_FILES:
        text = _scrub_allowed_required_names(_read(path)).lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_product_files_do_not_import_timeline_or_highlight_selector():
    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]

    for path in PRODUCT_FILES:
        text = _read(path)
        for word in forbidden:
            assert word not in text, f"{word} found in {path}"


def test_no_bom_and_newline_for_all_2b31_files():
    for path in PRODUCT_FILES + TEST_FILES + [PIPELINE_FILE, REGISTRY_FILE, JOB_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
