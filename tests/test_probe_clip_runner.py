import pytest


def test_parse_args_probe_clip_mode(tmp_path):
    """--output-dir aktiviert Probe-Clip-Modus."""
    import pipeline_runner

    fake_video = tmp_path / "test.mp4"
    fake_video.touch()

    args = pipeline_runner._parse_args(
        [
            str(fake_video),
            "--output-dir",
            str(tmp_path / "out"),
            "--start-sec",
            "5.0",
            "--duration",
            "15.0",
        ]
    )

    assert args.output_dir is not None
    assert args.start_sec == 5.0
    assert args.duration == 15.0


def test_parse_args_probe_clip_conflicts_with_approve(tmp_path):
    """--output-dir darf nicht mit --approve kombiniert werden."""
    import pipeline_runner

    fake_video = tmp_path / "test.mp4"
    fake_video.touch()

    with pytest.raises(SystemExit):
        pipeline_runner._parse_args(
            [
                str(fake_video),
                "--approve",
                "job_123",
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
