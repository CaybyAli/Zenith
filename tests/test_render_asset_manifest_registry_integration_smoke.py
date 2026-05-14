from __future__ import annotations

from pathlib import Path

from core.render_asset_manifest_signal_adapter import build_render_asset_manifest_signals
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _job_with_manifest() -> dict:
    return {
        "job_id": "job_render_asset_registry_smoke",
        "render_asset_manifest_report": {
            "status": "render_asset_manifest_ready_with_warnings",
            "dry_run_only": True,
            "manifest_only": True,
            "paths_are_hints_only": True,
            "can_create_directories": False,
            "can_write_files": False,
            "can_open_media": False,
            "can_render": False,
            "can_run_ffmpeg": False,
            "asset_references": [
                {
                    "asset_id": "asset_primary",
                    "asset_type": "primary_media",
                    "path_hint": "inputs/raw/gameplay.mp4",
                    "required": True,
                    "safety_status": "hint_only",
                    "warnings": [],
                    "blocking_reasons": [],
                },
                {
                    "asset_id": "asset_censor",
                    "asset_type": "censor_sfx_asset",
                    "path_hint": "assets/sfx/censor/censor_sfx_manifest.json",
                    "required": True,
                    "safety_status": "hint_only_with_warnings",
                    "warnings": ["censor_sfx_asset_is_hint_only"],
                    "blocking_reasons": [],
                },
            ],
            "output_path_plans": [
                {
                    "output_id": "main_youtube",
                    "output_type": "planned_video",
                    "platform": "youtube",
                    "safe_filename": "safe_output.mp4",
                    "path_safety_status": "hint_only_with_warnings",
                    "warnings": ["render_output_path_is_hint_only"],
                    "blocking_reasons": [],
                }
            ],
            "blocking_reasons": [],
            "warnings": ["render_output_path_is_hint_only"],
        },
    }


def test_signal_adapter_emits_manifest_asset_and_output_signals():
    signals = build_render_asset_manifest_signals(_job_with_manifest())

    signal_types = {signal["signal_type"] for signal in signals}

    assert "render_asset_manifest_ready_with_warnings" in signal_types
    assert "render_asset_reference_planned" in signal_types
    assert "render_output_path_planned" in signal_types
    assert "render_asset_censor_sfx_required" in signal_types
    assert "render_asset_manifest_only_confirmed" in signal_types
    assert "render_asset_paths_hint_only_confirmed" in signal_types
    assert "render_asset_render_not_allowed" in signal_types

    for signal in signals:
        assert signal["source"] == "render_asset_manifest"
        assert signal["action_hint"] == "review_render_asset_manifest"
        assert signal["metadata"]["render_asset_manifest_only"] is True
        assert signal["metadata"]["dry_run_only"] is True
        assert signal["metadata"]["paths_are_hints_only"] is True
        assert signal["metadata"]["media_unchanged"] is True


def test_registry_imports_render_asset_manifest_adapter_and_source():
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")

    assert "build_render_asset_manifest_signals" in text
    assert 'SOURCE_RENDER_ASSET_MANIFEST = "render_asset_manifest"' in text
    assert "render_asset_manifest_report" in text
    assert "render_asset_manifest" in text


def test_registry_collects_render_asset_manifest_signals():
    result = build_unified_edit_signal_result(_job_with_manifest())

    assert result.source_counts.get("render_asset_manifest", 0) > 0

    signal_types = {signal["signal_type"] for signal in result.signals}
    assert "render_asset_manifest_ready_with_warnings" in signal_types
    assert "render_asset_reference_planned" in signal_types
    assert "render_output_path_planned" in signal_types
