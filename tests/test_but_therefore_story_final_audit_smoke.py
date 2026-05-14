from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    "models/but_therefore_story.py",
    "core/but_therefore_story_engine.py",
    "core/but_therefore_story_runner.py",
    "core/but_therefore_story_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]

BUT_THEREFORE_FILES = [
    "models/but_therefore_story.py",
    "core/but_therefore_story_engine.py",
    "core/but_therefore_story_runner.py",
    "core/but_therefore_story_signal_adapter.py",
]

FORBIDDEN_IN_BUT_THEREFORE_FILES = [
    "subprocess",
    "os.system",
    "ffmpeg",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "execute_story",
    "remove_and_moment",
    "remove_and_moments",
    "auto_remove",
    "auto_trim",
]

ALLOWED_SAFETY_FIELD_TOKENS = [
    "can_reorder_timeline",
    "story_can_reorder_timeline",
    "no_timeline_reorder_in_2b_42",
    "can_remove_and_moments",
    "story_can_remove_and_moments",
    "no_and_moment_remove_in_2b_42",
    "can_trim",
    "story_can_trim",
    "can_extend",
    "story_can_extend",
    "can_render",
    "story_can_render",
    "no_render_in_2b_42",
    "can_apply_story_changes",
    "story_can_apply_changes",
    "no_story_apply_in_2b_42",
]


def _without_allowed_safety_fields(text: str) -> str:
    cleaned = text
    for token in ALLOWED_SAFETY_FIELD_TOKENS:
        cleaned = cleaned.replace(token, "")
    return cleaned


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_product_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES:
        content = (ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), relative_path
        assert content.endswith(b"\n"), relative_path


def test_but_therefore_files_do_not_contain_forbidden_media_execution_calls() -> None:
    for relative_path in BUT_THEREFORE_FILES:
        text = _without_allowed_safety_fields(_read(relative_path))
        for forbidden in FORBIDDEN_IN_BUT_THEREFORE_FILES:
            assert forbidden not in text, f"{forbidden} found in {relative_path}"


def test_review_only_safety_flags_are_present_in_product_files() -> None:
    required_tokens = [
        "review_only",
        "but_therefore_story_only",
        "media_unchanged",
        "no_execution_in_2b_42",
        "no_render_in_2b_42",
        "no_timeline_reorder_in_2b_42",
        "no_story_apply_in_2b_42",
        "no_and_moment_remove_in_2b_42",
    ]

    combined = "\n".join(_read(path) for path in PRODUCT_FILES)

    for token in required_tokens:
        assert token in combined


def test_story_capability_flags_are_always_false_in_models_runner_and_pipeline() -> None:
    combined = "\n".join(
        _read(path)
        for path in (
            "models/but_therefore_story.py",
            "core/but_therefore_story_runner.py",
            "core/gaming_pipeline.py",
            "models/job.py",
        )
    )

    required_false_tokens = [
        "can_apply_story_changes: bool = False",
        "can_remove_and_moments: bool = False",
        "can_reorder_timeline: bool = False",
        "can_trim: bool = False",
        "can_extend: bool = False",
        "can_render: bool = False",
        "story_can_apply_changes: bool = False",
        "story_can_remove_and_moments: bool = False",
        "story_can_reorder_timeline: bool = False",
        "story_can_trim: bool = False",
        "story_can_extend: bool = False",
        "story_can_render: bool = False",
        '"can_apply_story_changes": False',
        '"can_remove_and_moments": False',
        '"can_reorder_timeline": False',
        '"can_trim": False',
        '"can_extend": False',
        '"can_render": False',
    ]

    for token in required_false_tokens:
        assert token in combined


def test_pipeline_order_keeps_reaction_shot_before_but_therefore_story() -> None:
    text = _read("core/gaming_pipeline.py")

    assert text.index("reaction_shot_placement_engine_done") < text.index(
        "but_therefore_story_engine_done"
    )


def test_registry_includes_but_therefore_story_source() -> None:
    text = _read("core/unified_edit_signal_registry.py")

    assert 'SOURCE_BUT_THEREFORE_STORY = "but_therefore_story"' in text
    assert "adapt_but_therefore_story_report_to_signals" in text
    assert "source_counts[SOURCE_BUT_THEREFORE_STORY]" in text
