from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_unified_edit_signal_registry() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    assert "unified_edit_signal_registry" in source
    assert "run_unified_edit_signal_registry_for_job" in source


def test_pipeline_has_unified_edit_signal_section_after_audio_signal_modules() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    unified_idx = source.find("# ── Unified Edit Signal Registry (3-C)")
    beat_done_idx = source.find('step_name="beat_detection_done"')
    audio_norm_done_idx = source.find('step_name="audio_normalization_done"')
    filler_done_idx = source.find('step_name="filler_word_detection_done"')
    transcript_done_idx = source.find('step_name="transcript_done"')

    assert unified_idx > 0, "Unified edit signal block missing"
    assert beat_done_idx > 0
    assert audio_norm_done_idx > 0
    assert filler_done_idx > 0
    assert transcript_done_idx > 0
    assert unified_idx > beat_done_idx, "Registry must come AFTER beat_detection"
    assert unified_idx > audio_norm_done_idx
    assert unified_idx > filler_done_idx
    assert unified_idx > transcript_done_idx


def test_pipeline_emits_all_unified_signal_decision_events() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "UNIFIED_EDIT_SIGNALS_STARTED" in source
    assert "UNIFIED_EDIT_SIGNALS_DONE" in source
    assert "UNIFIED_EDIT_SIGNALS_SKIPPED" in source
    assert "UNIFIED_EDIT_SIGNALS_FAILED" in source


def test_pipeline_persists_unified_edit_signals_checkpoint() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    assert 'step_name="unified_edit_signals_done"' in source


def test_pipeline_block_is_wrapped_in_try_except() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    start = source.find("# ── Unified Edit Signal Registry (3-C)")
    end = source.find("# ── End Unified Edit Signal Registry")
    assert start > 0 and end > start

    block = source[start:end]
    assert "try:" in block
    assert "except Exception" in block
    assert "UNIFIED_EDIT_SIGNALS_FAILED" in block


def test_phase3c_pipeline_smoke_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/gaming_pipeline.py"),
        Path("core/unified_edit_signal_registry.py"),
        Path("models/unified_edit_signal_result.py"),
        Path("models/job.py"),
        Path("tests/test_phase3c_unified_edit_signal_registry_smoke.py"),
        Path("tests/test_phase3c_unified_edit_signal_pipeline_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
