from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.ffmpeg_helper import get_ffprobe_path
from core.shorts_generation_stage import ShortsGenerationStage
from core.shorts_highlight_extractor import LLM_SHADOW
from models.edit_timeline import EditTimeline
from models.job import Job
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


EXISTING_LONGFORM_SEGMENT_SECONDS = 60.0
EXISTING_LONGFORM_MAX_SEGMENTS = 12


def is_existing_longform_output_path(source_video_path: str | Path | None) -> bool:
    if not source_video_path:
        return False

    path = Path(source_video_path)
    if not path.exists() or path.suffix.lower() != ".mp4":
        return False

    if not path.name.lower().endswith("_final.mp4"):
        return False

    return (path.parent / "job.json").exists()


def _probe_duration_seconds(source_video_path: str | Path) -> float:
    ffprobe_path = get_ffprobe_path()
    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source_video_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "ffprobe_duration_failed: "
            + (result.stderr.strip() or str(source_video_path))
        )

    return max(0.0, float(result.stdout.strip() or 0.0))


def _load_sibling_job_payload(source_video_path: str | Path) -> dict:
    job_json_path = Path(source_video_path).parent / "job.json"
    if not job_json_path.exists():
        return {}

    try:
        return json.loads(job_json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_existing_longform_render_source(source_video_path: str | Path) -> Path:
    source_path = Path(source_video_path)
    payload = _load_sibling_job_payload(source_path)

    for key in ("raw_video_path", "input_file", "source_file", "file_path"):
        value = payload.get(key)
        if not value:
            continue
        candidate = Path(str(value))
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() == ".mp4":
            return candidate

    return source_path


def _load_transcript_from_sibling_job_json(source_video_path: str | Path) -> TranscriptResult | None:
    payload = _load_sibling_job_payload(source_video_path)
    if not payload:
        return None
    raw_segments = list(payload.get("transcript_segments") or [])
    if not raw_segments:
        report = payload.get("transcript_report")
        if isinstance(report, dict):
            raw_segments = list(report.get("segments") or [])

    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue

        words: list[TranscriptWord] = []
        for raw_word in list(raw_segment.get("words") or []):
            if not isinstance(raw_word, dict):
                continue
            try:
                words.append(
                    TranscriptWord(
                        text=str(raw_word.get("text") or raw_word.get("word") or "").strip(),
                        start_seconds=float(raw_word.get("start_seconds")),
                        end_seconds=float(raw_word.get("end_seconds")),
                        probability=raw_word.get("probability") or raw_word.get("confidence"),
                    )
                )
            except Exception:
                continue

        try:
            segments.append(
                TranscriptSegment(
                    start_seconds=float(raw_segment.get("start_seconds")),
                    end_seconds=float(raw_segment.get("end_seconds")),
                    text=str(raw_segment.get("text") or ""),
                    confidence=raw_segment.get("confidence"),
                    words=words,
                    audio_track=str(raw_segment.get("audio_track") or "mic"),
                    speaker=str(raw_segment.get("speaker") or "unknown"),
                )
            )
        except Exception:
            continue

    if not segments:
        return None

    full_text = str(payload.get("transcript_text") or "").strip()
    if not full_text:
        full_text = " ".join(segment.text for segment in segments if segment.text).strip()

    report = payload.get("transcript_report") if isinstance(payload.get("transcript_report"), dict) else {}

    return TranscriptResult(
        source_path=str(source_video_path),
        language=payload.get("transcript_language") or report.get("language"),
        segments=segments,
        full_text=full_text,
        engine=str(payload.get("transcription_engine") or report.get("engine") or "whisperx"),
    )




def build_existing_longform_shorts_timeline(
    job: Job,
    *,
    duration_seconds: float,
) -> EditTimeline:
    duration_seconds = max(0.0, float(duration_seconds))

    if duration_seconds <= 0.0:
        raise ValueError("existing_longform_duration_missing")

    window_duration = min(EXISTING_LONGFORM_SEGMENT_SECONDS, duration_seconds)

    if duration_seconds <= window_duration:
        starts = [0.0]
    else:
        possible_count = int(duration_seconds // window_duration)
        segment_count = max(1, min(EXISTING_LONGFORM_MAX_SEGMENTS, possible_count))
        if segment_count <= 1:
            starts = [0.0]
        else:
            max_start = max(0.0, duration_seconds - window_duration)
            step = max(window_duration, max_start / float(segment_count - 1))
            starts = [
                min(max_start, round(index * step, 3))
                for index in range(segment_count)
            ]

    selected_segments: list[TimelineSegment] = []
    for index, start in enumerate(starts):
        end = min(duration_seconds, start + window_duration)
        if end - start < 15.0:
            continue

        selected_segments.append(
            TimelineSegment(
                segment_id=f"existing_longform_seg_{index}",
                job_id=str(job.job_id),
                candidate_id=f"existing_longform_candidate_{index}",
                start_time=round(start, 3),
                end_time=round(end, 3),
                segment_role="highlight" if index else "hook",
                selection_score=round(max(0.5, 1.0 - (index * 0.03)), 3),
                notes=[
                    "existing_longform_output",
                    "shorts_floor_decoupled",
                    f"window_index={index}",
                ],
                source="existing_longform_shorts_stage",
            )
        )

    if not selected_segments:
        raise ValueError("existing_longform_no_valid_shorts_segments")

    return EditTimeline(
        timeline_id=f"existing_longform_timeline_{job.job_id}",
        job_id=str(job.job_id),
        target_duration=duration_seconds,
        selected_segments=selected_segments,
        timeline_score=round(
            sum(segment.selection_score for segment in selected_segments)
            / len(selected_segments),
            3,
        ),
        timeline_notes=[
            "Existing longform output reused for shorts generation",
            "Longform floor check unchanged",
            f"source_duration_seconds={duration_seconds:.3f}",
            f"segments={len(selected_segments)}",
        ],
    )


def run_shorts_from_existing_longform_output(
    *,
    job: Job,
    source_video_path: str | Path,
    output_base_dir: str | Path,
    power_profile: str = "balanced",
    llm_mode: str = LLM_SHADOW,
    add_captions: bool = True,
) -> dict:
    source_path = Path(source_video_path)
    render_source_path = _resolve_existing_longform_render_source(source_path)
    duration_seconds = _probe_duration_seconds(source_path)
    timeline = build_existing_longform_shorts_timeline(
        job,
        duration_seconds=duration_seconds,
    )

    transcript = _load_transcript_from_sibling_job_json(source_path)

    stage = ShortsGenerationStage()
    stage.run(
        job=job,
        timeline=timeline,
        source_video_path=str(render_source_path),
        output_base_dir=str(output_base_dir),
        power_profile=str(power_profile),
        llm_mode=str(llm_mode),
        add_captions=add_captions,
        transcript=transcript,
    )

    return {
        "job": job,
        "final_job_status": getattr(getattr(job, "status", ""), "value", job.status),
        "final_video_path": str(source_path),
        "shorts_render_source_path": str(render_source_path),
        "shorts_from_existing_longform": True,
        "shorts_count": len(getattr(job, "shorts_clips", []) or []),
        "existing_longform_duration_seconds": duration_seconds,
        "caption_transcript_loaded": transcript is not None,
    }
