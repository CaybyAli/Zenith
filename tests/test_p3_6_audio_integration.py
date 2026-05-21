import shutil
import subprocess

import pytest

from core.audio_normalizer import AudioNormalizer


@pytest.mark.ffmpeg_integration
def test_audio_normalization_produces_output(tmp_path):
    """Echter Pass-1-Lauf mit Dummy-Audio. JSON wird geparst. skipped=False."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg not available")

    input_path = tmp_path / "dummy_audio.wav"

    create_audio = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=0.5",
            "-y",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert create_audio.returncode == 0
    assert input_path.exists()

    normalizer = AudioNormalizer()
    command = normalizer.build_pass1_command(str(input_path))
    command[0] = ffmpeg

    pass1 = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    measured = normalizer.parse_pass1_output(
        (pass1.stderr or "") + "\n" + (pass1.stdout or "")
    )
    result = normalizer.build_result(measured)

    assert pass1.returncode == 0
    assert measured
    assert result.skipped is False
    assert result.filter_string.startswith("loudnorm=")
