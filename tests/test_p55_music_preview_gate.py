from pathlib import Path

import pytest

from core.music_preview_gate import (
    MusicPreviewGateError,
    PreviewGateInput,
    build_empty_music_preview_gate_manifest,
    evaluate_music_preview_gate,
    validate_preview_gate_decision,
)
from scripts.p55_music_preview_gate_smoke import run


def _gate_input(**overrides):
    item = {
        "channel_type": "main",
        "owner_preview_go": True,
        "phase_5_done": True,
        "p5_l_closed": True,
        "music_library_verified": True,
        "selector_ready": True,
        "ducking_plan_ready": True,
        "uncut_music_allowed": False,
        "music_files_tracked": False,
        "music_files_staged": False,
        "render_requested": False,
        "audio_mix_requested": False,
        "qwen_requested": False,
        "runtime_learning_requested": False,
        "external_download_requested": False,
        "api_key_present": False,
    }
    item.update(overrides)
    return item


def test_main_without_owner_preview_go_waits_for_owner_go():
    decision = evaluate_music_preview_gate(_gate_input(owner_preview_go=False))
    assert decision.preview_allowed is False
    assert decision.gate_status == "waiting_for_owner_go"
    assert "owner_preview_go_required" in decision.reason


def test_main_with_owner_preview_go_and_clean_gate_is_ready():
    decision = evaluate_music_preview_gate(_gate_input())
    assert decision.preview_allowed is True
    assert decision.gate_status == "ready_for_controlled_preview"


def test_ready_gate_still_starts_no_music_build_or_render():
    decision = evaluate_music_preview_gate(_gate_input())
    assert decision.safety_flags["music_build_started"] is False
    assert decision.safety_flags["music_inserted"] is False
    assert decision.safety_flags["audio_mix_started"] is False
    assert decision.safety_flags["render_used"] is False


def test_uncut_is_always_blocked():
    decision = evaluate_music_preview_gate(_gate_input(channel_type="uncut"))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "uncut_music_disabled" in decision.reason


def test_render_requested_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(render_requested=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "render_not_allowed_in_gate" in decision.reason


def test_audio_mix_requested_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(audio_mix_requested=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "audio_mix_not_allowed_in_gate" in decision.reason


def test_qwen_requested_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(qwen_requested=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_runtime_learning_requested_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(runtime_learning_requested=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_external_download_requested_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(external_download_requested=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_api_key_present_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(api_key_present=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_music_files_tracked_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(music_files_tracked=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_music_files_staged_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(music_files_staged=True))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"


def test_missing_music_library_verification_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(music_library_verified=False))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "music_library_not_verified" in decision.reason


def test_missing_selector_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(selector_ready=False))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "selector_not_ready" in decision.reason


def test_missing_ducking_plan_blocks_gate():
    decision = evaluate_music_preview_gate(_gate_input(ducking_plan_ready=False))
    assert decision.preview_allowed is False
    assert decision.gate_status == "blocked"
    assert "ducking_plan_not_ready" in decision.reason


def test_manifest_default_is_safe():
    manifest = build_empty_music_preview_gate_manifest()
    for flag in (
        "music_build_started",
        "music_inserted",
        "audio_mix_started",
        "real_audio_modified",
        "render_used",
        "preview_render_used",
        "ingest_used",
        "qwen_used",
        "qwen_autocut_used",
        "runtime_learning_started",
        "external_download_used",
        "api_key_used",
        "music_files_committed",
    ):
        assert manifest[flag] is False
    assert manifest["uncut_music_allowed"] is False


def test_smoke_script_writes_only_expected_reports_dir(tmp_path):
    manifest = run(str(tmp_path), "reports/phase5_5_music_preview_gate")
    assert manifest["status"] == "ok"
    assert manifest["step"] == "5.5-6"
    assert manifest["mode"] == "controlled_music_preview_gate_only"
    assert (tmp_path / "reports/phase5_5_music_preview_gate/music_preview_gate_manifest.json").exists()
    assert (tmp_path / "reports/phase5_5_music_preview_gate/music_preview_gate_summary.md").exists()
    assert not (tmp_path / "video_configs").exists()
    assert not (tmp_path / "learning_corpus").exists()
    assert not (tmp_path / "local_assets/music").exists()


def test_wrong_output_dir_is_blocked(tmp_path):
    for output_dir in (
        "reports/other",
        "video_configs",
        "learning_corpus",
        "local_assets/music",
    ):
        with pytest.raises(ValueError):
            run(str(tmp_path), output_dir)
        assert not (tmp_path / output_dir).exists()


def test_preview_gate_input_exposes_qwen_requested_contract():
    gate_input = PreviewGateInput(**_gate_input(qwen_requested=True))
    assert gate_input.qwen_requested is True


def test_validate_preview_gate_decision_rejects_unsafe_manifest_flag():
    decision = evaluate_music_preview_gate(_gate_input())
    decision.safety_flags["music_build_started"] = True
    with pytest.raises(MusicPreviewGateError):
        validate_preview_gate_decision(decision)


def test_forbidden_imports_and_usage_are_absent():
    forbidden = (
        "subprocess",
        "requests",
        "ffmpeg",
        "whisper",
        "render_short",
        "shutil.rmtree",
        "os.remove",
        ".unlink(",
        "while True",
        "ollama",
        "qwen",
    )
    for path in (
        Path("core/music_preview_gate.py"),
        Path("scripts/p55_music_preview_gate_smoke.py"),
    ):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text
