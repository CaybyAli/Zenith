from __future__ import annotations

from types import SimpleNamespace

from core.shorts_source_format_detector import ShortsSourceFormatDetector


def test_shorts_source_format_detector_detects_32_9_composite(monkeypatch) -> None:
    captured = {}

    def fake_run(cmd, capture_output, text, check):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return SimpleNamespace(stdout='{"streams":[{"width":3840,"height":1080}]}')

    monkeypatch.setattr("core.shorts_source_format_detector.subprocess.run", fake_run)

    result = ShortsSourceFormatDetector.detect("dummy.mp4", ffprobe_binary="fake-ffprobe")

    assert captured["cmd"][:2] == ["fake-ffprobe", "-v"]
    assert result.width == 3840
    assert result.height == 1080
    assert result.aspect_ratio == 3840 / 1080
    assert result.is_32_9_composite is True
    assert result.gameplay_region == (0, 0, 1920, 1080)
    assert result.facecam_region == (1920, 0, 1920, 1080)
