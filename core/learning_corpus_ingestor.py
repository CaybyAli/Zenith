from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path


@dataclass(frozen=True)
class AudioPreparationResult:
    """Result of the mandatory corpus audio input preparation step."""

    source_path: Path
    prepared_path: Path
    audio_stream_count: int
    mixed: bool
    skipped_existing: bool
    power_profile: str | None = None


class LearningCorpusIngestor:
    """
    Scaffold for Phase 5 learning corpus ingestion.

    P5-1A only owns the first mandatory media-safety step:
    every video input is probed before ingestion and multi-audio inputs are
    mixed into a deterministic sidecar file next to the original media.

    The power_profile hook is accepted and stored now so later GPU/CPU-bound
    submodules can receive the same setting without changing the public
    ingestor interface. This P5-1A audio preparation step itself is FFmpeg-
    bound and does not alter FFmpeg flags based on power_profile.
    """

    def __init__(
        self,
        corpus_root: str | Path = Path("learning_corpus"),
        *,
        power_profile: str | None = None,
        ffmpeg_path: str | None = None,
        ffprobe_path: str | None = None,
    ) -> None:
        self.corpus_root = Path(corpus_root)
        self.power_profile = power_profile
        self._ffmpeg_path = ffmpeg_path
        self._ffprobe_path = ffprobe_path

    def ffmpeg_path(self) -> str:
        return self._ffmpeg_path or get_ffmpeg_path()

    def ffprobe_path(self) -> str:
        return self._ffprobe_path or get_ffprobe_path()

    def iter_video_folders(self) -> Iterable[Path]:
        """Yield known Phase-5 corpus video folders in deterministic order."""

        sections = (
            self.corpus_root / "pairs",
            self.corpus_root / "top_main",
            self.corpus_root / "vlogs",
        )
        for section in sections:
            if not section.exists():
                continue
            for folder in sorted(path for path in section.iterdir() if path.is_dir()):
                yield folder

    def prepare_pair_audio(self, pair_path: str | Path) -> AudioPreparationResult:
        """Prepare pair_NNN/raw.mp4 and always return raw_mixed_audio.mp4."""

        source_path = Path(pair_path) / "raw.mp4"
        expected_output = source_path.with_name("raw_mixed_audio.mp4")
        existed_before = expected_output.exists()
        prepared_path = ensure_mixed_audio(
            pair_path,
            ffmpeg_path=self.ffmpeg_path(),
            ffprobe_path=self.ffprobe_path(),
        )
        audio_count = probe_audio_stream_count(source_path, ffprobe_path=self.ffprobe_path())
        return AudioPreparationResult(
            source_path=source_path,
            prepared_path=prepared_path,
            audio_stream_count=audio_count,
            mixed=audio_count > 1,
            skipped_existing=existed_before,
            power_profile=self.power_profile,
        )

    def prepare_final_audio(self, video_path: str | Path) -> AudioPreparationResult:
        """
        Prepare top_main/vlogs final.mp4 inputs.

        final.mp4 is used directly when it has a single audio stream. If it has
        multiple audio streams, a final_mixed_audio.mp4 sidecar is created.
        """

        source_path = Path(video_path)
        expected_output = source_path.with_name("final_mixed_audio.mp4")
        existed_before = expected_output.exists()
        prepared_path = ensure_video_audio_ready(
            source_path,
            mixed_filename="final_mixed_audio.mp4",
            copy_single_stream=False,
            ffmpeg_path=self.ffmpeg_path(),
            ffprobe_path=self.ffprobe_path(),
        )
        audio_count = probe_audio_stream_count(source_path, ffprobe_path=self.ffprobe_path())
        return AudioPreparationResult(
            source_path=source_path,
            prepared_path=prepared_path,
            audio_stream_count=audio_count,
            mixed=prepared_path.name == "final_mixed_audio.mp4" and audio_count > 1,
            skipped_existing=existed_before,
            power_profile=self.power_profile,
        )

    def prepare_video_folder(self, video_folder: str | Path) -> AudioPreparationResult:
        """
        Run the first mandatory ingest check for one corpus folder.

        pairs/pair_NNN use raw.mp4 and produce raw_mixed_audio.mp4.
        top_main/video_NNN and vlogs/vlog_NNN use final.mp4 unless that file
        contains multiple audio streams, in which case final_mixed_audio.mp4 is
        produced and returned.
        """

        folder = Path(video_folder)
        if folder.parent.name == "pairs":
            return self.prepare_pair_audio(folder)

        final_path = folder / "final.mp4"
        if final_path.exists():
            return self.prepare_final_audio(final_path)

        raw_path = folder / "raw.mp4"
        if raw_path.exists():
            expected_output = raw_path.with_name("raw_mixed_audio.mp4")
            existed_before = expected_output.exists()
            prepared = ensure_video_audio_ready(
                raw_path,
                mixed_filename="raw_mixed_audio.mp4",
                copy_single_stream=True,
                ffmpeg_path=self.ffmpeg_path(),
                ffprobe_path=self.ffprobe_path(),
            )
            audio_count = probe_audio_stream_count(raw_path, ffprobe_path=self.ffprobe_path())
            return AudioPreparationResult(
                source_path=raw_path,
                prepared_path=prepared,
                audio_stream_count=audio_count,
                mixed=audio_count > 1,
                skipped_existing=existed_before,
                power_profile=self.power_profile,
            )

        raise FileNotFoundError(f"No supported corpus video found in {folder}")


def probe_audio_stream_count(video_path: str | Path, *, ffprobe_path: str | None = None) -> int:
    """
    Return the number of audio streams in a media file using ffprobe.

    Equivalent command:
    ffprobe -v quiet -select_streams a -show_entries stream=index -of csv=p=0 input.mp4
    """

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Input video does not exist: {path}")

    command = [
        ffprobe_path or get_ffprobe_path(),
        "-v",
        "quiet",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return len(lines)


def ensure_mixed_audio(
    pair_path: str | Path,
    *,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> Path:
    """
    Ensure pair_NNN/raw_mixed_audio.mp4 exists and return its path.

    If raw.mp4 has one audio stream, raw.mp4 is copied to raw_mixed_audio.mp4.
    If raw.mp4 has multiple audio streams, all audio streams are merged with
    FFmpeg amerge into raw_mixed_audio.mp4.
    If raw_mixed_audio.mp4 already exists, it is returned unchanged.
    """

    pair_dir = Path(pair_path)
    return ensure_video_audio_ready(
        pair_dir / "raw.mp4",
        mixed_filename="raw_mixed_audio.mp4",
        copy_single_stream=True,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )


def ensure_video_audio_ready(
    input_video_path: str | Path,
    *,
    mixed_filename: str,
    copy_single_stream: bool,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> Path:
    """
    Prepare a video input for downstream transcript/audio analysis.

    - Existing sidecar output is never regenerated.
    - One audio stream returns the original input unless copy_single_stream=True.
    - More than one audio stream creates a mixed sidecar next to the input.
    """

    input_path = Path(input_video_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input video does not exist: {input_path}")

    output_path = input_path.with_name(mixed_filename)
    if output_path.exists():
        return output_path

    audio_count = probe_audio_stream_count(input_path, ffprobe_path=ffprobe_path)
    if audio_count < 1:
        raise ValueError(f"Input video has no audio stream: {input_path}")

    if audio_count == 1:
        if copy_single_stream:
            _copy_video(input_path, output_path)
            return output_path
        return input_path

    return mix_audio_streams(
        input_path,
        output_path,
        audio_stream_count=audio_count,
        ffmpeg_path=ffmpeg_path,
    )


def mix_audio_streams(
    input_video_path: str | Path,
    output_video_path: str | Path,
    *,
    audio_stream_count: int,
    ffmpeg_path: str | None = None,
) -> Path:
    """Merge all audio streams from input_video_path into output_video_path."""

    if audio_stream_count < 2:
        raise ValueError("mix_audio_streams requires at least two audio streams")

    input_path = Path(input_video_path)
    output_path = Path(output_video_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    input_labels = "".join(f"[0:a:{index}]" for index in range(audio_stream_count))
    filter_complex = f"{input_labels}amerge=inputs={audio_stream_count}[aout]"
    temp_output = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")

    if temp_output.exists():
        temp_output.unlink()

    command = [
        ffmpeg_path or get_ffmpeg_path(),
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(temp_output),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        temp_output.replace(output_path)
    finally:
        if temp_output.exists():
            temp_output.unlink()

    return output_path


def _copy_video(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    if temp_output.exists():
        temp_output.unlink()

    try:
        shutil.copy2(input_path, temp_output)
        temp_output.replace(output_path)
    finally:
        if temp_output.exists():
            temp_output.unlink()
