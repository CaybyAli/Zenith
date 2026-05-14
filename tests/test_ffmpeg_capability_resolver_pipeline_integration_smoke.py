from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_and_runs_ffmpeg_capability_after_controlled_executor() -> None:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_ff_tool_capability_resolver" in text
    assert '"FF" "MPEG_CAPABILITY_RESOLVER_STARTED"' in text
    assert '"ff" "mpeg_capability_resolver_done"' in text

    controlled_index = text.index("controlled_render_executor_done")
    tool_index = text.index('"FF" "MPEG_CAPABILITY_RESOLVER_STARTED"')

    assert controlled_index < tool_index
    assert '"phase": "2B-52"' in text
    assert '"no_render_in_2b_52": True' in text
    assert '"no_media_input_in_2b_52": True' in text
    assert '"no_media_output_in_2b_52": True' in text
    assert '"controlled_tool_probe_only": True' in text
