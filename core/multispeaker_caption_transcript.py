from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from core.audio_track_mapping_config import AudioTrackRole, load_audio_track_mapping_config
from core.ffmpeg_helper import get_ffmpeg_path
from core.transcript_processor import TranscriptProcessor
from core.caption_transcription_config import resolve_caption_whisper_model
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord

LOGGER = logging.getLogger(__name__)


def build_multispeaker_caption_transcript_for_clip(
    *,
    source_video_path: str | Path,
    clip_start_seconds: float,
    clip_end_seconds: float,
    config_dir: str | Path = "video_configs",
    transcript_processor: TranscriptProcessor | None = None,
) -> TranscriptResult | None:
    config = load_audio_track_mapping_config(source_video_path, config_dir=config_dir)
    if config is None:
        return None

    tracks = config.caption_tracks()
    if not tracks:
        return None

    source = Path(source_video_path)
    if not source.exists():
        LOGGER.warning("multi-speaker caption source missing: %s", source)
        return None

    clip_start = float(clip_start_seconds)
    clip_end = float(clip_end_seconds)
    duration = max(0.0, clip_end - clip_start)
    if duration <= 0.0:
        return None

    processor = transcript_processor or TranscriptProcessor(
            transcription_engine=os.getenv("ZENITH_TRANSCRIPTION_ENGINE", "whisperx"),
            model_name=resolve_caption_whisper_model(
                source_video_path=source_video_path,
                config_dir=config_dir,
            ).model_name,
        )

    transcript_results: list[TranscriptResult] = []

    with tempfile.TemporaryDirectory(prefix="zenith_multispeaker_caption_") as temp_dir:
        temp_root = Path(temp_dir)

        for track in tracks:
            sample_path = temp_root / f"{track.audio_track}_0a{track.ffmpeg_audio_index}.wav"
            extracted = _extract_track_clip(
                source_video_path=source,
                ffmpeg_audio_index=track.ffmpeg_audio_index,
                clip_start_seconds=clip_start,
                duration_seconds=duration,
                output_path=sample_path,
            )
            if not extracted:
                LOGGER.warning(
                    "multi-speaker caption track extract failed role=%s track=%s index=%s",
                    track.role,
                    track.audio_track,
                    track.ffmpeg_audio_index,
                )
                continue

            try:
                raw_result = processor.transcribe(str(sample_path))
            except Exception as exc:
                # Stille Friend-Spur oder leere Spur: kein Fehler, nur keine Friend-W?rter.
                LOGGER.warning(
                    "multi-speaker caption transcription skipped role=%s track=%s error=%s",
                    track.role,
                    track.audio_track,
                    exc,
                )
                continue

            stamped = stamp_transcript_result_for_caption_track(
                raw_result,
                track=track,
                clip_start_seconds=clip_start,
                result_source_path=str(source),
            )
            if stamped.segments:
                transcript_results.append(stamped)

    if not transcript_results:
        return None

    return merge_caption_transcript_results(
        transcript_results,
        source_path=str(source),
    )


def _extract_track_clip(
    *,
    source_video_path: Path,
    ffmpeg_audio_index: int,
    clip_start_seconds: float,
    duration_seconds: float,
    output_path: Path,
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-v",
        "error",
        "-ss",
        f"{float(clip_start_seconds):.3f}",
        "-i",
        str(source_video_path),
        "-t",
        f"{float(duration_seconds):.3f}",
        "-map",
        f"0:a:{int(ffmpeg_audio_index)}",
        "-vn",
        "-ar",
        "48000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if completed.returncode != 0:
        LOGGER.warning(
            "ffmpeg audio track extract failed index=%s stderr=%s",
            ffmpeg_audio_index,
            (completed.stderr or completed.stdout or "").strip()[-800:],
        )
        return False

    return output_path.exists() and output_path.stat().st_size > 0


def stamp_transcript_result_for_caption_track(
    result: TranscriptResult,
    *,
    track: AudioTrackRole,
    clip_start_seconds: float,
    result_source_path: str,
) -> TranscriptResult:
    offset = float(clip_start_seconds)
    segments: list[TranscriptSegment] = []

    for segment in result.segments or []:
        segment_start = float(segment.start_seconds) + offset
        segment_end = float(segment.end_seconds) + offset
        words: list[TranscriptWord] = []

        for word in segment.words or []:
            words.append(
                TranscriptWord(
                    start_seconds=round(float(word.start_seconds) + offset, 3),
                    end_seconds=round(float(word.end_seconds) + offset, 3),
                    text=str(word.text or "").strip(),
                    probability=word.probability,
                    audio_track=track.audio_track,
                    speaker=track.speaker,
                )
            )

        segments.append(
            TranscriptSegment(
                start_seconds=round(segment_start, 3),
                end_seconds=round(segment_end, 3),
                text=str(segment.text or "").strip(),
                confidence=segment.confidence,
                words=words,
                audio_track=track.audio_track,
                speaker=track.speaker,
            )
        )

    return TranscriptResult(
        source_path=result_source_path,
        language=result.language,
        segments=segments,
        full_text=" ".join(segment.text for segment in segments if segment.text).strip(),
        engine=f"{result.engine}:{track.audio_track}",
    )


def merge_caption_transcript_results(
    results: Iterable[TranscriptResult],
    *,
    source_path: str,
) -> TranscriptResult:
    collected = list(results)
    segments: list[TranscriptSegment] = []
    languages: list[str] = []
    engines: list[str] = []

    for result in collected:
        if result.language:
            languages.append(str(result.language))
        engines.append(str(result.engine))
        segments.extend(list(result.segments or []))

    segments.sort(
        key=lambda segment: (
            float(segment.start_seconds),
            _speaker_priority(segment.speaker, segment.audio_track),
            float(segment.end_seconds),
        )
    )

    return TranscriptResult(
        source_path=source_path,
        language=languages[0] if languages else None,
        segments=segments,
        full_text=" ".join(segment.text for segment in segments if segment.text).strip(),
        engine="+".join(engines) if engines else "multi_speaker_caption",
    )


def _speaker_priority(speaker: str, audio_track: str) -> int:
    marker = f"{speaker} {audio_track}".casefold()
    if any(item in marker for item in ("ali", "owner", "mic", "hajar", "primary", "main")):
        return 0
    return 1
