from __future__ import annotations

from typing import Any, Callable

from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError
from core.transcript_source_selector import (
    TranscriptSourceSelection,
    select_transcript_source_for_job,
)
from models.transcript_result import TranscriptResult
from models.transcript_run import TranscriptRunReport


TranscribeFn = Callable[[str], TranscriptResult]


def _serialize_segments(result: TranscriptResult) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []

    for segment in result.segments or []:
        to_dict = getattr(segment, "to_dict", None)
        if callable(to_dict):
            try:
                segments.append(dict(to_dict()))
                continue
            except Exception:
                pass

        segments.append(
            {
                "start_seconds": float(getattr(segment, "start_seconds", 0.0) or 0.0),
                "end_seconds": float(getattr(segment, "end_seconds", 0.0) or 0.0),
                "text": str(getattr(segment, "text", "") or ""),
                "confidence": getattr(segment, "confidence", None),
            }
        )

    return segments


def _word_count(full_text: str) -> int:
    if not full_text:
        return 0

    return len([part for part in full_text.split() if part.strip()])


def _duration_seconds(segments: list[dict[str, Any]]) -> float:
    if not segments:
        return 0.0

    max_end = 0.0
    for segment in segments:
        try:
            end_value = float(segment.get("end_seconds") or 0.0)
        except (TypeError, ValueError):
            continue
        if end_value > max_end:
            max_end = end_value

    return max_end


def _blocked_report(
    selection: TranscriptSourceSelection,
    metadata: dict[str, Any],
) -> TranscriptRunReport:
    selection_dict = selection.to_dict()
    status_text = selection.status or ""

    if status_text == "blocked_missing_preprocessed_audio":
        status = "blocked_missing_preprocessed_audio"
        recommendation = "generate_preprocessed_audio"
    elif status_text == "skipped_no_audio_source":
        status = "skipped_no_audio_source"
        recommendation = "no_audio_source_available"
    elif status_text == "failed":
        status = "failed"
        recommendation = "fix_transcript_source"
    else:
        status = "skipped_no_audio_source"
        recommendation = selection.recommendation or "no_audio_source_available"

    return TranscriptRunReport(
        status=status,
        source_path=selection.selected_path,
        source_type=selection.selected_type,
        source_selection=selection_dict,
        recommendation=recommendation,
        warnings=list(selection.warnings),
        errors=list(selection.errors),
        metadata=dict(metadata),
    )


def _run_transcribe(
    transcribe_fn: TranscribeFn,
    source_path: str,
) -> tuple[TranscriptResult | None, str | None, str | None]:
    try:
        result = transcribe_fn(source_path)
        return result, None, None
    except TranscriptUnavailableError as exc:
        return None, "whisper_unavailable", str(exc)
    except FileNotFoundError as exc:
        return None, "source_missing", str(exc)
    except Exception as exc:
        return None, "transcript_runner_exception", str(exc)


def build_transcript_run_report(
    selection: TranscriptSourceSelection,
    transcribe_fn: TranscribeFn,
    metadata: dict[str, Any] | None = None,
) -> TranscriptRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    if selection.status not in {"selected", "selected_fallback"}:
        return _blocked_report(selection, safe_metadata)

    if not selection.selected_path:
        return _blocked_report(selection, safe_metadata)

    result, error_kind, error_message = _run_transcribe(
        transcribe_fn=transcribe_fn,
        source_path=selection.selected_path,
    )

    warnings: list[str] = list(selection.warnings)
    errors: list[str] = []

    if result is None:
        if error_kind == "whisper_unavailable":
            return TranscriptRunReport(
                status="whisper_unavailable",
                source_path=selection.selected_path,
                source_type=selection.selected_type,
                source_selection=selection.to_dict(),
                recommendation="install_whisper_engine",
                warnings=warnings + ["whisper_unavailable"],
                errors=[error_message] if error_message else ["whisper_unavailable"],
                metadata=safe_metadata,
            )

        if error_kind == "source_missing":
            return TranscriptRunReport(
                status="blocked_missing_preprocessed_audio",
                source_path=selection.selected_path,
                source_type=selection.selected_type,
                source_selection=selection.to_dict(),
                recommendation="generate_preprocessed_audio",
                warnings=warnings,
                errors=[error_message] if error_message else ["source_missing"],
                metadata=safe_metadata,
            )

        return TranscriptRunReport(
            status="failed",
            source_path=selection.selected_path,
            source_type=selection.selected_type,
            source_selection=selection.to_dict(),
            recommendation="retry_or_fix_transcript",
            warnings=warnings,
            errors=[error_message or "transcript_runner_exception"],
            metadata=safe_metadata,
        )

    segments = _serialize_segments(result)
    full_text = (result.full_text or "").strip()
    duration_seconds = _duration_seconds(segments)
    word_count = _word_count(full_text)

    if not segments or not full_text:
        warnings.append("transcript_empty")
        status = "completed_with_warnings"
        recommendation = "transcript_empty_review"
    elif warnings:
        status = "completed_with_warnings"
        recommendation = "transcript_completed_with_warnings"
    else:
        status = "ok"
        recommendation = "use_transcript"

    return TranscriptRunReport(
        status=status,
        source_path=selection.selected_path,
        source_type=selection.selected_type,
        source_selection=selection.to_dict(),
        engine=getattr(result, "engine", None),
        language=getattr(result, "language", None),
        segments=segments,
        full_text=full_text,
        segment_count=len(segments),
        duration_seconds=duration_seconds,
        word_count=word_count,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=safe_metadata,
    )


def run_transcript_for_job(
    job: Any,
    transcript_processor: TranscriptProcessor | None = None,
    allow_raw_video_fallback: bool = True,
    require_existing_file: bool = True,
    metadata: dict[str, Any] | None = None,
) -> TranscriptRunReport:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    selection = select_transcript_source_for_job(
        job=job,
        allow_raw_video_fallback=allow_raw_video_fallback,
        require_existing_file=require_existing_file,
        metadata={"stage": safe_metadata.get("stage")},
    )

    processor = transcript_processor or TranscriptProcessor()

    report = build_transcript_run_report(
        selection=selection,
        transcribe_fn=processor.transcribe,
        metadata=safe_metadata,
    )

    return report


def apply_transcript_run_report_to_job(
    job: Any,
    report: TranscriptRunReport,
) -> Any:
    report_dict = report.to_dict()

    job.transcript_report = report_dict
    job.transcript_status = report.status
    job.transcript_source_path = report.source_path
    job.transcript_source_type = report.source_type
    job.transcript_segments = list(report.segments)
    job.transcript_text = report.full_text
    job.transcript_segment_count = int(report.segment_count or 0)
    job.transcript_duration_seconds = float(report.duration_seconds or 0.0)
    job.transcript_language = report.language
    job.transcript_recommendation = report.recommendation

    if hasattr(job, "touch"):
        job.touch()

    return job
