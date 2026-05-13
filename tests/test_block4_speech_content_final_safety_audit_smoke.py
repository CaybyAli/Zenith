from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


BLOCK4_SAFETY_FILES = [
    "core/transcript_runner.py",
    "core/transcript_segment_normalizer.py",
    "core/sentence_boundary_protector.py",
    "core/sentence_boundary_runner.py",
    "core/sentence_boundary_signal_adapter.py",
    "core/keyword_emotion_scorer.py",
    "core/keyword_emotion_runner.py",
    "core/keyword_emotion_signal_adapter.py",
    "core/interaction_classifier.py",
    "core/interaction_classification_runner.py",
    "core/interaction_classification_signal_adapter.py",
    "core/dead_content_detector.py",
    "core/dead_content_runner.py",
    "core/dead_content_signal_adapter.py",
    "core/content_value_calculator.py",
    "core/content_value_runner.py",
    "core/content_value_signal_adapter.py",
    "core/gaming_pipeline.py",
]


FORBIDDEN_AUTO_ACTION_STRINGS = [
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
]


FORBIDDEN_DIRECT_CUT_BINDINGS = [
    "LongformTimelineBuilder",
    "HighlightSelector",
    "build_timeline",
    "apply_cut",
    "render_now",
]


PRIVATE_REVIEW_REQUIRED = [
    "private_or_meta_candidate",
    "review_private_or_meta_candidate",
]


PRIVATE_FORBIDDEN = [
    "auto_remove_private",
    "censor_now",
    "delete_private",
]


HOOK_REVIEW_REQUIRED = [
    "review_hook_candidate",
]


HOOK_FORBIDDEN = [
    "auto_hook",
    "highlight_now",
]


DEAD_CONTENT_REVIEW_ALLOWED = [
    "review_dead_content",
    "review_dead_content_candidate",
    "review_low_value_content_candidate",
]


DEAD_CONTENT_FORBIDDEN = [
    "hard_remove",
    "auto_remove",
    "drop_segment",
]


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _read_text(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def _combined_text() -> str:
    return "\n".join(_read_text(path) for path in BLOCK4_SAFETY_FILES)


def _assert_file_clean(relative_path: str) -> None:
    data = _path(relative_path).read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf"), f"File has UTF-8 BOM: {relative_path}"
    assert data.endswith(b"\n"), f"File does not end with newline: {relative_path}"


def test_block4_product_files_do_not_contain_automatic_cut_remove_highlight_actions() -> None:
    for relative_path in BLOCK4_SAFETY_FILES:
        text = _read_text(relative_path)
        forbidden_found = [
            token for token in FORBIDDEN_AUTO_ACTION_STRINGS
            if token in text
        ]

        assert not forbidden_found, (
            f"Forbidden automatic action strings in {relative_path}: "
            f"{forbidden_found}"
        )


def test_block4_signal_files_do_not_bind_directly_to_timeline_or_highlight_selector() -> None:
    block4_signal_files = [
        path for path in BLOCK4_SAFETY_FILES
        if path != "core/gaming_pipeline.py"
    ]

    for relative_path in block4_signal_files:
        text = _read_text(relative_path)
        forbidden_found = [
            token for token in FORBIDDEN_DIRECT_CUT_BINDINGS
            if token in text
        ]

        assert not forbidden_found, (
            f"Forbidden direct cut binding in {relative_path}: "
            f"{forbidden_found}"
        )


def test_private_or_meta_content_stays_review_only() -> None:
    text = _combined_text()

    missing = [token for token in PRIVATE_REVIEW_REQUIRED if token not in text]
    forbidden_found = [token for token in PRIVATE_FORBIDDEN if token in text]

    assert not missing, f"Missing private/meta review markers: {missing}"
    assert not forbidden_found, f"Forbidden private/meta auto action found: {forbidden_found}"


def test_hook_candidates_stay_review_only() -> None:
    text = _combined_text()

    missing = [token for token in HOOK_REVIEW_REQUIRED if token not in text]
    forbidden_found = [token for token in HOOK_FORBIDDEN if token in text]

    assert not missing, f"Missing hook review markers: {missing}"
    assert not forbidden_found, f"Forbidden hook auto action found: {forbidden_found}"


def test_dead_content_stays_review_only() -> None:
    text = _combined_text()

    assert any(token in text for token in DEAD_CONTENT_REVIEW_ALLOWED), (
        "Missing dead-content review marker. Expected one of: "
        f"{DEAD_CONTENT_REVIEW_ALLOWED}"
    )

    forbidden_found = [token for token in DEAD_CONTENT_FORBIDDEN if token in text]

    assert not forbidden_found, f"Forbidden dead-content auto action found: {forbidden_found}"


def test_block4_safety_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in BLOCK4_SAFETY_FILES:
        _assert_file_clean(relative_path)
