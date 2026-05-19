from __future__ import annotations

from pathlib import Path


def test_final_render_driver_smoke_uses_resolver_for_encoder_assertion() -> None:
    """Guard against reintroducing a stale hardcoded NVENC assertion."""
    source = Path("tests/test_final_render_driver_smoke.py").read_text(encoding="utf-8")

    assert 'ctx["codec_video"] == "h264_nvenc"' not in source
    assert "_resolve_video_encoder" in source
    assert 'ctx["codec_video"] == resolved["codec"]' in source
    assert 'ctx["video_encoder_mode"] == resolved["mode"]' in source
