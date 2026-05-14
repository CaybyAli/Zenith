from __future__ import annotations

from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities


def test_resolver_blocks_empty_ffmpeg_path() -> None:
    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_empty_path",
            "ffmpeg_path_hint": "",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        }
    )

    assert report.status == "ffmpeg_capability_blocked"
    assert "ffmpeg_path_empty" in report.blocking_reasons
    assert report.tool_probe_attempted is False
    assert report.can_render is False
    assert report.can_process_media is False
    assert report.can_write_media is False
    assert report.can_probe_media_files is False


def test_resolver_blocks_path_traversal() -> None:
    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_traversal",
            "ffmpeg_path_hint": r"..\ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        }
    )

    assert report.status == "ffmpeg_capability_blocked"
    assert "ffmpeg_path_traversal_blocked" in report.blocking_reasons


def test_resolver_blocks_url_path() -> None:
    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_url",
            "ffmpeg_path_hint": "https://example.test/ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        }
    )

    assert report.status == "ffmpeg_capability_blocked"
    assert "ffmpeg_path_url_blocked" in report.blocking_reasons


def test_resolver_blocks_shell_marker_path() -> None:
    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_shell",
            "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe & calc.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        }
    )

    assert report.status == "ffmpeg_capability_blocked"
    assert "ffmpeg_path_shell_marker_blocked" in report.blocking_reasons


def test_resolver_blocks_wrong_tool_filename() -> None:
    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_wrong_tool",
            "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\not_ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
        }
    )

    assert report.status == "ffmpeg_capability_blocked"
    assert "ffmpeg_path_wrong_tool_name" in report.blocking_reasons


def test_resolver_warns_without_tool_probe_and_does_not_probe() -> None:
    calls: list[list[str]] = []

    def fake_probe(argv: list[str]) -> tuple[bool, str, str]:
        calls.append(argv)
        return True, "", ""

    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_no_probe",
            "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
            "ffmpeg_resolver_allow_tool_probe": False,
        },
        probe_runner=fake_probe,
    )

    assert report.status == "ffmpeg_capability_ready_with_warnings"
    assert "ffmpeg_tool_probe_not_allowed" in report.warnings
    assert calls == []
    assert report.tool_probe_attempted is False
    assert report.tool_probe_succeeded is False


def test_resolver_mocked_probe_detects_versions_and_capabilities() -> None:
    calls: list[list[str]] = []

    def fake_probe(argv: list[str]) -> tuple[bool, str, str]:
        calls.append(argv)
        joined = " ".join(argv)
        if "-version" in joined:
            if "ffprobe" in argv[0].lower():
                return True, "ffprobe version 7.0-test\n", ""
            return True, "ffmpeg version 7.0-test\n", ""
        if "-encoders" in joined:
            return True, " V....D libx264\n A..... aac\n V....D h264_nvenc\n", ""
        if "-decoders" in joined:
            return True, " V....D h264\n", ""
        if "-filters" in joined:
            return True, " ..C scale\n ... loudnorm\n ... concat\n", ""
        if "-hwaccels" in joined:
            return True, "Hardware acceleration methods:\ncuda\nd3d11va\n", ""
        return False, "", "unexpected_probe"

    report = resolve_ffmpeg_capabilities(
        {
            "job_id": "job_probe",
            "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
            "ffprobe_path_hint": r"D:\Tools\ffmpeg\bin\ffprobe.exe",
            "ffmpeg_resolver_allow_tool_probe": True,
        },
        probe_runner=fake_probe,
    )

    assert report.status == "ffmpeg_capability_ready"
    assert report.tool_probe_attempted is True
    assert report.tool_probe_succeeded is True
    assert report.ffmpeg_version == "ffmpeg version 7.0-test"
    assert report.ffprobe_version == "ffprobe version 7.0-test"
    assert report.has_h264 is True
    assert report.has_aac is True
    assert report.has_nvenc is True
    assert report.has_scale_filter is True
    assert report.has_concat_support is True
    assert report.has_loudnorm_filter is True
    assert report.can_prepare_real_render_tools is True
    assert report.can_render is False
    assert report.can_process_media is False
    assert report.can_write_media is False
    assert report.can_probe_media_files is False

    assert calls == [
        [r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-version"],
        [r"D:\Tools\ffmpeg\bin\ffprobe.exe", "-version"],
        [r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-encoders"],
        [r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-decoders"],
        [r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-filters"],
        [r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-hwaccels"],
    ]
