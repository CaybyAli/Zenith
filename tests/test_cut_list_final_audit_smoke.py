from pathlib import Path

from core.cut_list_signal_adapter import adapt_cut_list_report_to_signals
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "cut_list.py",
    ROOT / "core" / "cut_list_generator.py",
    ROOT / "models" / "cut_list_run.py",
    ROOT / "core" / "cut_list_runner.py",
    ROOT / "core" / "cut_list_signal_adapter.py",
]

CHANGED_PRODUCT_FILES = PRODUCT_FILES + [
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_cut_list_generator_foundation_smoke.py",
    ROOT / "tests" / "test_cut_list_runner_smoke.py",
    ROOT / "tests" / "test_cut_list_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_signal_adapter_smoke.py",
    ROOT / "tests" / "test_cut_list_registry_integration_smoke.py",
    ROOT / "tests" / "test_cut_list_final_audit_smoke.py",
]

FORBIDDEN_OPERATIONAL_TERMS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
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
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pipeline_cut_list_block() -> str:
    text = _text(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("# ── Cut List Generation (2B-27-C)")
    end = text.index("# ── End Cut List Generation", start)
    return text[start:end]


def _make_job(extra=None):
    data = {
        "job_id": "job_cut_list_final_audit",
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
    if extra:
        data.update(extra)
    return Job.from_dict(data)


def _cut_list_item(action: str, index: int):
    return {
        "item_id": f"item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 5),
        "center_seconds": float(index * 10 + 2.5),
        "duration_seconds": 5.0,
        "proposed_action": action,
        "action_confidence": 0.8,
        "priority": "medium",
        "segment_type": "test",
        "murch_score": 0.7,
        "content_value_score": 0.6,
        "risk_score": 0.1,
        "protection_score": 0.0,
        "censor_required": action == "CENSOR_KEEP",
        "is_protected": action == "PROTECT",
        "is_review_required": action != "KEEP",
        "reason": f"reason {action}",
        "decision_basis": {"test": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_all_2b27_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), str(path)


def test_all_2b27_test_files_exist():
    for path in TEST_FILES:
        assert path.exists(), str(path)


def test_job_has_cut_list_fields():
    job = _make_job()
    data = job.to_dict()

    required_fields = [
        "cut_list_report",
        "cut_list_status",
        "cut_list_items",
        "cut_list_item_count",
        "cut_list_keep_count",
        "cut_list_review_keep_count",
        "cut_list_review_trim_count",
        "cut_list_review_remove_count",
        "cut_list_protect_count",
        "cut_list_censor_keep_count",
        "cut_list_technical_review_count",
        "cut_list_unknown_review_count",
        "cut_list_recommendation",
    ]

    for field in required_fields:
        assert hasattr(job, field)
        assert field in data


def test_pipeline_contains_cut_list_generation_block():
    block = _pipeline_cut_list_block()

    assert "CUT_LIST_GENERATION_STARTED" in block
    assert "CUT_LIST_GENERATION_DONE" in block
    assert "CUT_LIST_GENERATION_SKIPPED" in block
    assert "CUT_LIST_GENERATION_FAILED" in block
    assert 'step_name="cut_list_generation_done"' in block
    assert "run_cut_list_generation_for_job(" in block
    assert "apply_cut_list_run_report_to_job(" in block
    assert "try:" in block
    assert "except Exception as cut_list_generation_exc:" in block


def test_pipeline_cut_list_position_is_after_murch_scoring():
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    assert text.index("CUT_LIST_GENERATION_STARTED") > text.index("MURCH_SCORING_DONE")
    assert text.index('step_name="cut_list_generation_done"') > text.index(
        'step_name="murch_scoring_done"'
    )


def test_registry_imports_and_processes_cut_list_generator():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "from core.cut_list_signal_adapter import adapt_cut_list_report_to_signals" in text
    assert 'SOURCE_CUT_LIST_GENERATOR = "cut_list_generator"' in text
    assert "cut_list_report" in text
    assert "cut_list_items" in text
    assert "adapt_cut_list_report_to_signals(cut_list_report)" in text
    assert "source_counts[SOURCE_CUT_LIST_GENERATOR]" in text


def test_registry_cut_list_block_is_after_murch_scoring_block():
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert text.index("murch_scoring_signals = _safe_collect") < text.index(
        "cut_list_signals = _safe_collect"
    )


def test_signal_adapter_emits_all_cut_list_signal_types():
    result = adapt_cut_list_report_to_signals(
        {
            "items": [
                _cut_list_item("KEEP", 1),
                _cut_list_item("REVIEW_KEEP", 2),
                _cut_list_item("REVIEW_TRIM", 3),
                _cut_list_item("REVIEW_REMOVE", 4),
                _cut_list_item("PROTECT", 5),
                _cut_list_item("CENSOR_KEEP", 6),
                _cut_list_item("TECHNICAL_REVIEW", 7),
                _cut_list_item("UNKNOWN_REVIEW", 8),
            ]
        }
    )

    types = {signal["signal_type"] for signal in result.signals}

    assert "cut_list_keep_candidate" in types
    assert "cut_list_review_keep" in types
    assert "cut_list_review_trim" in types
    assert "cut_list_review_remove" in types
    assert "cut_list_protect_segment" in types
    assert "cut_list_censor_keep" in types
    assert "cut_list_technical_review" in types
    assert "cut_list_unknown_review" in types


def test_registry_runtime_counts_cut_list_generator_signals():
    job = _make_job(
        {
            "cut_list_report": {
                "status": "ok",
                "items": [
                    _cut_list_item("KEEP", 1),
                    _cut_list_item("REVIEW_KEEP", 2),
                    _cut_list_item("REVIEW_TRIM", 3),
                    _cut_list_item("REVIEW_REMOVE", 4),
                    _cut_list_item("PROTECT", 5),
                    _cut_list_item("CENSOR_KEEP", 6),
                    _cut_list_item("TECHNICAL_REVIEW", 7),
                    _cut_list_item("UNKNOWN_REVIEW", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["cut_list_generator"] == 8
    assert result.type_counts["cut_list_keep_candidate"] == 1
    assert result.type_counts["cut_list_review_keep"] == 1
    assert result.type_counts["cut_list_review_trim"] == 1
    assert result.type_counts["cut_list_review_remove"] == 1
    assert result.type_counts["cut_list_protect_segment"] == 1
    assert result.type_counts["cut_list_censor_keep"] == 1
    assert result.type_counts["cut_list_technical_review"] == 1
    assert result.type_counts["cut_list_unknown_review"] == 1


def test_review_remove_stays_review_and_censor_keep_stays_preserve_signal():
    result = adapt_cut_list_report_to_signals(
        {
            "items": [
                _cut_list_item("REVIEW_REMOVE", 1),
                _cut_list_item("CENSOR_KEEP", 2),
            ]
        }
    )

    by_type = {signal["signal_type"]: signal for signal in result.signals}

    assert by_type["cut_list_review_remove"]["action_hint"] == "review_remove_candidate"
    assert by_type["cut_list_censor_keep"]["action_hint"] == "preserve_segment_for_censor_sfx"


def test_2b27_product_files_do_not_contain_forbidden_operational_terms():
    allowed_safe_names = [
        "apply_cut_list_run_report_to_job",
    ]

    for path in PRODUCT_FILES:
        lowered = _text(path).lower()

        for allowed in allowed_safe_names:
            lowered = lowered.replace(allowed.lower(), "")

        for word in FORBIDDEN_OPERATIONAL_TERMS:
            assert word not in lowered, f"{word} found in {path}"


def test_pipeline_cut_list_block_has_no_timeline_highlight_render_or_ffmpeg_execution():
    block = _pipeline_cut_list_block()
    lowered = block.lower().replace("apply_cut_list_run_report_to_job", "")

    forbidden = FORBIDDEN_OPERATIONAL_TERMS + [
        "timelinebuilder",
        "highlightselector",
        "ffmpeg",
        "renderer.",
        ".render(",
        "renderprocessor",
    ]

    for word in forbidden:
        assert word not in lowered, f"{word} found in cut list pipeline block"


def test_2b27_files_have_no_bom_and_end_with_newline():
    for path in CHANGED_PRODUCT_FILES + TEST_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), str(path)
        assert raw.endswith(b"\n"), str(path)
