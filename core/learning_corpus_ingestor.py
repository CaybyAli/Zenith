from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.learning_corpus_audio_profile import extract_audio_profile
from core.learning_corpus_fingerprint_writer import (
    validate_style_fingerprint,
    write_style_fingerprint,
)
from core.learning_corpus_hook_identifier import identify_hook
from core.learning_corpus_pacing_metrics import extract_pacing_metrics
from core.learning_corpus_reaction_timing import extract_reaction_timing
from core.learning_corpus_scene_change import extract_scene_changes, probe_media_duration_seconds
from core.learning_corpus_transcript import extract_transcript


@dataclass(frozen=True)
class AudioPreparationResult:
    source_path: Path
    prepared_path: Path
    audio_stream_count: int
    mixed: bool
    skipped_existing: bool
    power_profile: str | None = None


@dataclass(frozen=True)
class IngestedVideoResult:
    video_folder: Path
    source_video_path: Path
    prepared_audio_path: Path
    fingerprint_path: Path
    audio_stream_count: int
    mixed_audio: bool
    power_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("video_folder", "source_video_path", "prepared_audio_path", "fingerprint_path"):
            payload[key] = str(payload[key])
        return payload


@dataclass(frozen=True)
class IngestRunResult:
    corpus_root: Path
    videos_processed: int
    fingerprints_written: list[Path]

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_root": str(self.corpus_root),
            "videos_processed": self.videos_processed,
            "fingerprints_written": [str(path) for path in self.fingerprints_written],
        }


TranscriptExtractor = Callable[..., dict[str, Any]]
SceneChangeExtractor = Callable[..., dict[str, Any]]
AudioProfileExtractor = Callable[..., dict[str, Any]]
HookExtractor = Callable[..., dict[str, Any]]
ReactionTimingExtractor = Callable[..., dict[str, Any]]


class LearningCorpusIngestor:
    """
    Orchestrator for Phase 5 learning corpus ingestion.

    First action per video:
    - probe audio stream count
    - create raw_mixed_audio.mp4 for pairs
    - create final_mixed_audio.mp4 for top_main/vlogs only when needed

    power_profile is passed into transcript extraction. Other P5-1 modules are
    local deterministic FFmpeg/text processors and currently do not need
    profile-specific flags.
    """

    def __init__(
        self,
        corpus_root: str | Path = Path("learning_corpus"),
        *,
        power_profile: str | None = None,
        ffmpeg_path: str | None = None,
        ffprobe_path: str | None = None,
        transcript_extractor: TranscriptExtractor = extract_transcript,
        scene_change_extractor: SceneChangeExtractor = extract_scene_changes,
        audio_profile_extractor: AudioProfileExtractor = extract_audio_profile,
        hook_extractor: HookExtractor = identify_hook,
        reaction_timing_extractor: ReactionTimingExtractor = extract_reaction_timing,
    ) -> None:
        self.corpus_root = Path(corpus_root)
        self.power_profile = power_profile
        self._ffmpeg_path = ffmpeg_path
        self._ffprobe_path = ffprobe_path
        self.transcript_extractor = transcript_extractor
        self.scene_change_extractor = scene_change_extractor
        self.audio_profile_extractor = audio_profile_extractor
        self.hook_extractor = hook_extractor
        self.reaction_timing_extractor = reaction_timing_extractor

    def ffmpeg_path(self) -> str:
        return self._ffmpeg_path or get_ffmpeg_path()

    def ffprobe_path(self) -> str:
        return self._ffprobe_path or get_ffprobe_path()

    def iter_video_folders(self) -> Iterable[Path]:
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

    def ingest_all(self) -> IngestRunResult:
        fingerprints: list[Path] = []
        for folder in self.iter_video_folders():
            result = self.ingest_video_folder(folder)
            fingerprints.append(result.fingerprint_path)

        return IngestRunResult(
            corpus_root=self.corpus_root,
            videos_processed=len(fingerprints),
            fingerprints_written=fingerprints,
        )

    def ingest_video_folder(self, video_folder: str | Path) -> IngestedVideoResult:
        folder = Path(video_folder)
        meta = read_meta_json(folder / "meta.json")
        audio_preparation = self.prepare_video_folder(folder)

        transcript = self.transcript_extractor(
            audio_preparation.prepared_path,
            power_profile=self.power_profile,
        )

        scene_source = choose_scene_source(folder, audio_preparation.source_path)
        scene_changes = self.scene_change_extractor(
            scene_source,
            ffmpeg_path=self.ffmpeg_path(),
            ffprobe_path=self.ffprobe_path(),
        )

        audio = self.audio_profile_extractor(
            audio_preparation.prepared_path,
            ffmpeg_path=self.ffmpeg_path(),
            ffprobe_path=self.ffprobe_path(),
        )

        duration_seconds = probe_media_duration_seconds(
            scene_source,
            ffprobe_path=self.ffprobe_path(),
        )
        pacing = extract_pacing_metrics(
            scene_changes.get("boundaries_seconds", []),
            duration_seconds=duration_seconds,
        )

        hook = self.hook_extractor(transcript)

        reaction_timing = self.reaction_timing_extractor(
            video_type=meta.get("type"),
            meta=meta,
            transcript=transcript,
            scene_changes=scene_changes,
        )

        fingerprint_path = write_style_fingerprint(
            folder,
            meta=meta,
            transcript=transcript,
            scene_changes=scene_changes,
            audio=audio,
            pacing=pacing,
            hook=hook,
            reaction_timing=reaction_timing,
        )

        fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))
        validate_style_fingerprint(fingerprint)

        return IngestedVideoResult(
            video_folder=folder,
            source_video_path=audio_preparation.source_path,
            prepared_audio_path=audio_preparation.prepared_path,
            fingerprint_path=fingerprint_path,
            audio_stream_count=audio_preparation.audio_stream_count,
            mixed_audio=audio_preparation.mixed,
            power_profile=self.power_profile,
        )

    def prepare_pair_audio(self, pair_path: str | Path) -> AudioPreparationResult:
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


def read_meta_json(meta_path: str | Path) -> dict[str, Any]:
    path = Path(meta_path)
    if not path.exists():
        raise FileNotFoundError(f"Missing meta.json: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"meta.json must contain an object: {path}")

    required = ("video_id", "type", "quality_tier")
    missing = [key for key in required if not str(payload.get(key, "")).strip()]
    if missing:
        raise ValueError(f"meta.json missing required fields {missing}: {path}")

    return payload


def choose_scene_source(video_folder: Path, fallback: Path) -> Path:
    final_path = video_folder / "final.mp4"
    if final_path.exists():
        return final_path
    return fallback


def probe_audio_stream_count(video_path: str | Path, *, ffprobe_path: str | None = None) -> int:
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


def ingest_learning_corpus(
    corpus_root: str | Path = Path("learning_corpus"),
    *,
    power_profile: str | None = None,
) -> IngestRunResult:
    return LearningCorpusIngestor(
        corpus_root=corpus_root,
        power_profile=power_profile,
    ).ingest_all()
