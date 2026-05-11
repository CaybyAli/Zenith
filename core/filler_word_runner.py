from __future__ import annotations

from typing import Any

from core.filler_word_detector import detect_filler_words, extract_word_items
from models.filler_word_run import FillerWordRunReport


def extract_transcript_source_from_job(job: Any) -> tuple[Any | None, str | None]:
    def _nonempty(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, (list, dict, str)) and not val:
            return False
        return True

    # Direct attributes in priority order
    direct_attrs = [
        ("transcript_data", "job.transcript_data"),
        ("transcript", "job.transcript"),
        ("word_segments", "job.word_segments"),
        ("speech_segments", "job.speech_segments"),
        ("transcript_segments", "job.transcript_segments"),
        ("whisper_segments", "job.whisper_segments"),
        ("analysis_transcript", "job.analysis_transcript"),
    ]
    for attr, label in direct_attrs:
        try:
            val = getattr(job, attr, None)
            if _nonempty(val):
                return val, label
        except Exception:
            continue

    # metadata fallback
    try:
        metadata = getattr(job, "metadata", None)
        if isinstance(metadata, dict):
            meta_keys = [
                ("transcript_data", "job.metadata[transcript_data]"),
                ("transcript", "job.metadata[transcript]"),
                ("word_segments", "job.metadata[word_segments]"),
                ("speech_segments", "job.metadata[speech_segments]"),
                ("whisper_segments", "job.metadata[whisper_segments]"),
            ]
            for key, label in meta_keys:
                try:
                    val = metadata.get(key)
                    if _nonempty(val):
                        return val, label
                except Exception:
                    continue
    except Exception:
        pass

    return None, None


def _build_transcript_preview(
    transcript_data: Any,
    transcript_source: str | None,
    transcript_word_count: int,
) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "type": type(transcript_data).__name__,
        "word_count": transcript_word_count,
        "source": transcript_source,
    }
    try:
        if isinstance(transcript_data, list):
            preview["item_count"] = len(transcript_data)
        elif isinstance(transcript_data, dict):
            preview["keys"] = list(transcript_data.keys())[:10]
    except Exception:
        pass
    return preview


def build_filler_word_run_report(
    transcript_data: Any | None = None,
    transcript_source: str | None = None,
    filler_lexicon: dict[str, dict[str, Any]] | None = None,
    detect_repeated_words: bool = True,
    repeat_max_gap_seconds: float = 0.35,
    max_occurrences: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> FillerWordRunReport:
    if metadata is None:
        metadata = {}

    warnings: list[str] = []
    errors: list[str] = []

    # No transcript
    if transcript_data is None or (isinstance(transcript_data, (list, dict, str)) and not transcript_data):
        warnings.append("no_transcript_available")
        return FillerWordRunReport(
            status="skipped_no_transcript",
            transcript_source=transcript_source,
            transcript_data_preview=_build_transcript_preview(transcript_data, transcript_source, 0),
            warnings=warnings,
            errors=errors,
            recommendation="no_transcript_available",
            metadata=metadata,
        )

    try:
        word_items = extract_word_items(transcript_data)
        transcript_word_count = len(word_items)

        if transcript_word_count == 0:
            warnings.append("no_words_available")
            return FillerWordRunReport(
                status="skipped_no_transcript",
                transcript_source=transcript_source,
                transcript_data_preview=_build_transcript_preview(transcript_data, transcript_source, 0),
                transcript_word_count=0,
                warnings=warnings,
                errors=errors,
                recommendation="no_transcript_available",
                metadata=metadata,
            )

        result = detect_filler_words(
            transcript_data,
            filler_lexicon=filler_lexicon,
            detect_repeated_words=detect_repeated_words,
            repeat_max_gap_seconds=repeat_max_gap_seconds,
            max_occurrences=max_occurrences,
            metadata=metadata,
        )

        occurrences = [occ.to_dict() for occ in result.occurrences]
        occurrence_count = result.occurrence_count
        remove_candidate_count = result.remove_candidate_count
        counts_by_filler_type = dict(result.counts_by_filler_type)
        counts_by_language = dict(result.counts_by_language)
        total_filler_duration_seconds = result.total_filler_duration_seconds

        filler_rate = occurrence_count / transcript_word_count if transcript_word_count > 0 else 0.0

        all_warnings = list(warnings) + list(result.warnings)
        all_errors = list(errors) + list(result.errors)

        detection_result = result.to_dict()
        preview = _build_transcript_preview(transcript_data, transcript_source, transcript_word_count)

        # Derive status and recommendation
        if result.status == "failed":
            status = "failed"
            recommendation = "retry_or_fix_transcript"
        elif occurrence_count > 0 and not all_warnings:
            status = "ok"
            recommendation = "use_filler_word_analysis"
        elif occurrence_count > 0 and all_warnings:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        else:
            all_warnings.append("no_fillers_detected")
            status = "completed_with_warnings"
            recommendation = "no_fillers_detected"

        return FillerWordRunReport(
            status=status,
            transcript_source=transcript_source,
            transcript_data_preview=preview,
            detection_result=detection_result,
            occurrences=occurrences,
            occurrence_count=occurrence_count,
            remove_candidate_count=remove_candidate_count,
            counts_by_filler_type=counts_by_filler_type,
            counts_by_language=counts_by_language,
            total_filler_duration_seconds=total_filler_duration_seconds,
            transcript_word_count=transcript_word_count,
            filler_rate=round(filler_rate, 6),
            warnings=all_warnings,
            errors=all_errors,
            recommendation=recommendation,
            metadata=metadata,
        )

    except Exception as exc:
        errors.append("filler_word_runner_failed")
        return FillerWordRunReport(
            status="failed",
            transcript_source=transcript_source,
            transcript_data_preview=_build_transcript_preview(transcript_data, transcript_source, 0),
            warnings=warnings,
            errors=errors,
            recommendation="retry_or_fix_transcript",
            metadata=metadata,
        )


def run_filler_word_detection_for_job(
    job: Any,
    transcript_data: Any | None = None,
    filler_lexicon: dict[str, dict[str, Any]] | None = None,
    detect_repeated_words: bool = True,
    repeat_max_gap_seconds: float = 0.35,
    max_occurrences: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> FillerWordRunReport:
    if transcript_data is not None:
        source = "provided_transcript_data"
    else:
        try:
            transcript_data, source = extract_transcript_source_from_job(job)
        except Exception:
            transcript_data = None
            source = None

    return build_filler_word_run_report(
        transcript_data=transcript_data,
        transcript_source=source,
        filler_lexicon=filler_lexicon,
        detect_repeated_words=detect_repeated_words,
        repeat_max_gap_seconds=repeat_max_gap_seconds,
        max_occurrences=max_occurrences,
        metadata=metadata,
    )
