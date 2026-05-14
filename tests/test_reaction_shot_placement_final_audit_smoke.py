from __future__ import annotations

from pathlib import Path

from models.reaction_shot_placement import ReactionShotPlacementReport


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "reaction_shot_placement.py",
    ROOT / "core" / "reaction_shot_placement_engine.py",
    ROOT / "core" / "reaction_shot_placement_runner.py",
    ROOT / "core" / "reaction_shot_placement_signal_adapter.py",
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

REACTION_SHOT_FULL_SCAN_FILES = {
    ROOT / "models" / "reaction_shot_placement.py",
    ROOT / "core" / "reaction_shot_placement_engine.py",
    ROOT / "core" / "reaction_shot_placement_runner.py",
    ROOT / "core" / "reaction_shot_placement_signal_adapter.py",
}

FORBIDDEN_MEDIA_TOKENS = [
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
    "apply_reaction",
    "execute_reaction",
    "insert_reaction",
    "place_reaction",
    "move_facecam",
    "insert_zoom",
    "apply_zoom",
    "insert_overlay",
    "apply_overlay",
    "insert_sfx",
    "apply_sfx",
]

ALLOWED_SAFETY_FIELD_TOKENS = [
    "can_apply_reaction_shots",
    "reaction_shot_can_apply",
    "can_render",
    "reaction_shot_can_render",
    "no_render_in_2b_41",
    "can_insert_clip",
    "reaction_shot_can_insert_clip",
    "no_reaction_insert_in_2b_41",
    "can_move_clip",
    "reaction_shot_can_move_clip",
    "can_reorder_timeline",
    "reaction_shot_can_reorder_timeline",
    "no_timeline_reorder_in_2b_41",
    "no_reaction_apply_in_2b_41",
    "no_facecam_move_in_2b_41",
    "no_zoom_insert_in_2b_41",
    "no_sfx_insert_in_2b_40",
    "final_quality_can_apply_fixes",
    "final_quality_can_render",
    "final_quality_can_execute_timeline",
    "final_quality_can_reorder_timeline",
    "final_quality_can_trim",
    "final_quality_can_extend",
    "final_quality_can_insert_effects",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _between(text: str, start_token: str, end_token: str | None = None) -> str:
    start = text.find(start_token)
    assert start != -1, f"Missing start token: {start_token}"
    if end_token is None:
        return text[start:]
    end = text.find(end_token, start)
    assert end != -1, f"Missing end token: {end_token}"
    return text[start:end]


def _reaction_shot_relevant_text(path: Path) -> str:
    text = _text(path)

    if path in REACTION_SHOT_FULL_SCAN_FILES:
        return text

    if path.name == "gaming_pipeline.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.reaction_shot_placement_runner import",
                    "from core.audio_normalization_runner import",
                ),
                _between(
                    text,
                    "run_reaction_shot_placement_for_job(",
                    'step_name="reaction_shot_placement_engine_done"',
                ),
            ]
        )

    if path.name == "unified_edit_signal_registry.py":
        return "\n".join(
            [
                _between(
                    text,
                    "from core.reaction_shot_placement_signal_adapter import",
                    "from models.unified_edit_signal_result import",
                ),
                _between(
                    text,
                    "reaction_shot_placement_report = _job_attr",
                    "if final_cut_list_signals:",
                ),
            ]
        )

    if path.name == "job.py":
        return "\n".join(
            [
                _between(
                    text,
                    "reaction_shot_placement_report: dict",
                    "silence_detection_report: dict",
                ),
                _between(
                    text,
                    "reaction_shot_placement_report=dict",
                    "silence_detection_report=dict",
                ),
            ]
        )

    return text


def _without_allowed_safety_fields(text: str) -> str:
    cleaned = text
    for token in ALLOWED_SAFETY_FIELD_TOKENS:
        cleaned = cleaned.replace(token, "")
    return cleaned


def test_reaction_shot_product_files_exist() -> None:
    missing = [
        path.relative_to(ROOT).as_posix()
        for path in PRODUCT_FILES
        if not path.exists()
    ]

    assert missing == []


def test_reaction_shot_product_files_have_no_bom_and_end_with_newline() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        content = path.read_bytes()
        if content.startswith(b"\xef\xbb\xbf"):
            violations.append(f"{path.relative_to(ROOT)}:bom")
        if not content.endswith(b"\n"):
            violations.append(f"{path.relative_to(ROOT)}:missing_newline")

    assert violations == []


def test_reaction_shot_has_no_forbidden_media_operations() -> None:
    violations: list[str] = []

    for path in PRODUCT_FILES:
        text = _without_allowed_safety_fields(
            _reaction_shot_relevant_text(path)
        )
        for token in FORBIDDEN_MEDIA_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}:{token}")

    assert violations == []


def test_reaction_shot_report_forces_review_only_contract() -> None:
    report = ReactionShotPlacementReport.from_dict(
        {
            "status": "reaction_placement_ready",
            "review_required": False,
            "can_apply_reaction_shots": True,
            "can_move_clip": True,
            "can_insert_clip": True,
            "can_trim": True,
            "can_extend": True,
            "can_reorder_timeline": True,
            "can_render": True,
            "metadata": {},
        }
    )
    data = report.to_dict()

    assert data["review_required"] is True
    assert data["can_apply_reaction_shots"] is False
    assert data["can_move_clip"] is False
    assert data["can_insert_clip"] is False
    assert data["can_trim"] is False
    assert data["can_extend"] is False
    assert data["can_reorder_timeline"] is False
    assert data["can_render"] is False
    assert data["metadata"]["review_only"] is True
    assert data["metadata"]["reaction_shot_placement_only"] is True
    assert data["metadata"]["media_unchanged"] is True
    assert data["metadata"]["no_execution_in_2b_41"] is True
    assert data["metadata"]["no_render_in_2b_41"] is True
    assert data["metadata"]["no_timeline_reorder_in_2b_41"] is True
    assert data["metadata"]["no_reaction_apply_in_2b_41"] is True
    assert data["metadata"]["no_reaction_insert_in_2b_41"] is True
    assert data["metadata"]["no_facecam_move_in_2b_41"] is True
    assert data["metadata"]["no_zoom_insert_in_2b_41"] is True


def test_reaction_shot_static_pipeline_order_after_pattern_interrupt() -> None:
    text = _text(ROOT / "core" / "gaming_pipeline.py")

    pattern_index = text.index("run_pattern_interrupt_for_job(")
    pattern_apply_index = text.index("store_pattern_interrupt_run_report_to_job(")
    reaction_index = text.index("run_reaction_shot_placement_for_job(")
    reaction_apply_index = text.index(
        "store_reaction_shot_placement_run_report_to_job("
    )

    assert pattern_index < pattern_apply_index < reaction_index < reaction_apply_index


def test_reaction_shot_static_registry_source_exists() -> None:
    text = _text(ROOT / "core" / "unified_edit_signal_registry.py")

    assert 'SOURCE_REACTION_SHOT_PLACEMENT = "reaction_shot_placement"' in text
    assert "adapt_reaction_shot_placement_report_to_signals" in text
    assert "reaction_shot_placement_report" in text
