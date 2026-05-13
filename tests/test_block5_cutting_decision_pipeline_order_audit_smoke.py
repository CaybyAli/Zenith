from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"

EVENT_PREFIXES = [
    "UNIFIED_EDIT_SIGNALS",
    "SEGMENT_CLASSIFICATION",
    "MURCH_SCORING",
    "CUT_LIST_GENERATION",
    "CLIP_DURATION_OPTIMIZATION",
    "TRANSITION_DECISION",
    "CONTINUITY_CHECK",
    "CUT_LIST_FINALIZATION",
]

CHECKPOINTS_IN_ORDER = [
    'step_name="unified_edit_signals_done"',
    'step_name="segment_classification_done"',
    'step_name="murch_scoring_done"',
    'step_name="cut_list_generation_done"',
    'step_name="clip_duration_optimization_done"',
    'step_name="transition_decision_done"',
    'step_name="continuity_check_done"',
    'step_name="cut_list_finalization_done"',
]

CUTTING_FLOW_EVENTS_IN_ORDER = [
    'event_type="UNIFIED_EDIT_SIGNALS_DONE"',
    'event_type="SEGMENT_CLASSIFICATION_STARTED"',
    'event_type="MURCH_SCORING_STARTED"',
    'event_type="CUT_LIST_GENERATION_STARTED"',
    'event_type="CLIP_DURATION_OPTIMIZATION_STARTED"',
    'event_type="TRANSITION_DECISION_STARTED"',
    'event_type="CONTINUITY_CHECK_STARTED"',
    'event_type="CUT_LIST_FINALIZATION_STARTED"',
]

RUNNER_FUNCTIONS = [
    "run_segment_classification_for_job",
    "run_murch_scoring_for_job",
    "run_cut_list_generation_for_job",
    "run_clip_duration_optimization_for_job",
    "run_transition_decision_for_job",
    "run_continuity_check_for_job",
    "run_cut_list_finalization_for_job",
]

APPLY_FUNCTIONS = [
    "apply_segment_classification_run_report_to_job",
    "apply_murch_scoring_run_report_to_job",
    "apply_cut_list_run_report_to_job",
    "apply_clip_duration_run_report_to_job",
    "apply_transition_decision_run_report_to_job",
    "apply_continuity_check_run_report_to_job",
    "apply_cut_list_finalization_run_report_to_job",
]

GUARDED_BLOCKS = [
    ("UNIFIED_EDIT_SIGNALS_STARTED", 'step_name="unified_edit_signals_done"'),
    ("SEGMENT_CLASSIFICATION_STARTED", 'step_name="segment_classification_done"'),
    ("MURCH_SCORING_STARTED", 'step_name="murch_scoring_done"'),
    ("CUT_LIST_GENERATION_STARTED", 'step_name="cut_list_generation_done"'),
    (
        "CLIP_DURATION_OPTIMIZATION_STARTED",
        'step_name="clip_duration_optimization_done"',
    ),
    ("TRANSITION_DECISION_STARTED", 'step_name="transition_decision_done"'),
    ("CONTINUITY_CHECK_STARTED", 'step_name="continuity_check_done"'),
    ("CUT_LIST_FINALIZATION_STARTED", 'step_name="cut_list_finalization_done"'),
]


def _read_pipeline() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def _assert_tokens_in_order(text: str, tokens: list[str]) -> None:
    last_index = -1
    for token in tokens:
        assert token in text, token
        token_index = text.index(token)
        assert token_index > last_index, token
        last_index = token_index


def _block_between(text: str, start_event: str, end_checkpoint: str) -> str:
    start_token = f'event_type="{start_event}"'
    start = text.index(start_token)
    end = text.index(end_checkpoint, start)
    return text[start:end]


def test_pipeline_contains_all_block5_started_done_skipped_failed_events() -> None:
    text = _read_pipeline()

    for prefix in EVENT_PREFIXES:
        for suffix in ("STARTED", "DONE", "SKIPPED", "FAILED"):
            assert f'event_type="{prefix}_{suffix}"' in text


def test_pipeline_checkpoint_order_is_cutting_decision_order() -> None:
    _assert_tokens_in_order(_read_pipeline(), CHECKPOINTS_IN_ORDER)


def test_pipeline_block_event_order_is_cutting_decision_order() -> None:
    _assert_tokens_in_order(_read_pipeline(), CUTTING_FLOW_EVENTS_IN_ORDER)


def test_pipeline_imports_all_block5_runner_and_apply_functions() -> None:
    text = _read_pipeline()

    for function_name in RUNNER_FUNCTIONS + APPLY_FUNCTIONS:
        assert function_name in text


def test_each_cutting_decision_block_is_exception_guarded() -> None:
    text = _read_pipeline()

    for start_event, checkpoint in GUARDED_BLOCKS:
        block = _block_between(text, start_event, checkpoint)
        assert "try:" in block, start_event
        assert "except Exception as" in block, start_event


def test_pipeline_order_relationships_are_explicit() -> None:
    text = _read_pipeline()

    assert text.index('event_type="SEGMENT_CLASSIFICATION_STARTED"') > text.index(
        'event_type="UNIFIED_EDIT_SIGNALS_DONE"'
    )
    assert text.index('event_type="MURCH_SCORING_STARTED"') > text.index(
        'step_name="segment_classification_done"'
    )
    assert text.index('event_type="CUT_LIST_GENERATION_STARTED"') > text.index(
        'step_name="murch_scoring_done"'
    )
    assert text.index('event_type="CLIP_DURATION_OPTIMIZATION_STARTED"') > text.index(
        'step_name="cut_list_generation_done"'
    )
    assert text.index('event_type="TRANSITION_DECISION_STARTED"') > text.index(
        'step_name="clip_duration_optimization_done"'
    )
    assert text.index('event_type="CONTINUITY_CHECK_STARTED"') > text.index(
        'step_name="transition_decision_done"'
    )
    assert text.index('event_type="CUT_LIST_FINALIZATION_STARTED"') > text.index(
        'step_name="continuity_check_done"'
    )
