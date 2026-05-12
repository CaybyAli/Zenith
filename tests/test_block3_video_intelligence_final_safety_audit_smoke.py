from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


PRODUCT_FILES_TO_CHECK = [
    "core/scene_change_signal_adapter.py",
    "core/motion_analysis_signal_adapter.py",
    "core/face_reaction_signal_adapter.py",
    "core/stutter_detection_signal_adapter.py",
    "core/screen_content_signal_adapter.py",
    "core/visual_energy_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
]


FORBIDDEN_ACTION_HINTS = [
    "remove_now",
    "hard_remove",
    "auto_remove",
    "delete_segment",
    "force_cut",
    "auto_highlight",
    "auto_zoom",
    "render_now",
]


FORBIDDEN_DIRECT_CUT_DECISIONS = [
    "highlight_selector.select_from_visual",
    "timeline_builder.apply_visual",
    "cut_from_visual_energy",
    "remove_dead_visual_now",
    "auto_zoom_facecam_now",
]


AUDIT_FILES = [
    "tests/test_block3_video_intelligence_static_audit_smoke.py",
    "tests/test_block3_video_intelligence_unified_signal_audit_smoke.py",
    "tests/test_block3_video_intelligence_final_safety_audit_smoke.py",
]


def _path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def _read_text(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_block3_product_files_do_not_use_forbidden_action_hints() -> None:
    problems: list[str] = []

    for relative_path in PRODUCT_FILES_TO_CHECK:
        text = _read_text(relative_path)

        for forbidden in FORBIDDEN_ACTION_HINTS:
            forbidden_patterns = [
                f'"action_hint": "{forbidden}"',
                f"'action_hint': '{forbidden}'",
                f'action_hint = "{forbidden}"',
                f"action_hint = '{forbidden}'",
                f'return "{forbidden}"',
                f"return '{forbidden}'",
            ]

            for pattern in forbidden_patterns:
                if pattern in text:
                    problems.append(f"{relative_path}: forbidden action usage: {pattern}")

    assert not problems, "Forbidden automatic action hints found:\n" + "\n".join(problems)


def test_gaming_pipeline_does_not_make_direct_visual_cut_decisions() -> None:
    text = _read_text("core/gaming_pipeline.py")

    problems = [
        forbidden
        for forbidden in FORBIDDEN_DIRECT_CUT_DECISIONS
        if forbidden in text
    ]

    assert not problems, (
        "Gaming pipeline contains direct visual cut decisions:\n"
        + "\n".join(problems)
    )


def test_block3_safety_audit_confirms_review_only_video_intelligence() -> None:
    safe_review_markers = [
        "review",
        "candidate",
    ]

    for relative_path in [
        "core/scene_change_signal_adapter.py",
        "core/motion_analysis_signal_adapter.py",
        "core/face_reaction_signal_adapter.py",
        "core/stutter_detection_signal_adapter.py",
        "core/screen_content_signal_adapter.py",
        "core/visual_energy_signal_adapter.py",
    ]:
        text = _read_text(relative_path)

        assert "action_hint" in text, relative_path
        assert any(marker in text for marker in safe_review_markers), relative_path


def test_new_block3_audit_files_have_no_bom_and_end_with_newline() -> None:
    problems: list[str] = []

    for relative_path in AUDIT_FILES:
        content = _path(relative_path).read_bytes()

        if content.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{relative_path}: has UTF-8 BOM")

        if not content.endswith(b"\n"):
            problems.append(f"{relative_path}: does not end with newline")

    assert not problems, "Text hygiene problems:\n" + "\n".join(problems)
