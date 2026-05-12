from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    PipelineType,
    TargetFormat,
    ValidatorStatus,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Job:
    job_id: str
    job_type: JobType
    channel_type: ChannelType
    target_format: TargetFormat
    target_platforms: list[str]
    status: JobStatus
    mode: Mode

    autopublish_class: AutopublishClass
    confidence_score: float
    validator_status: ValidatorStatus

    raw_video_path: str | None = None
    shorts: list[dict[str, Any]] = field(default_factory=list)
    topic: str | None = None
    title: str | None = None
    pipeline_type: PipelineType | None = None
    profile_id: str | None = None
    quality_mode: str | None = None
    profile_version: str | None = None
    profile_snapshot_path: str | None = None
    profile_source: str | None = None
    profile_metadata: dict[str, Any] = field(default_factory=dict)
    state_history: list[dict[str, Any]] = field(default_factory=list)
    current_module: str | None = None
    error_message: str | None = None

    file_info: dict[str, Any] = field(default_factory=dict)
    file_acceptance: dict[str, Any] = field(default_factory=dict)
    stream_classification: dict[str, Any] = field(default_factory=dict)
    file_readability: dict[str, Any] = field(default_factory=dict)
    file_handler_report: dict[str, Any] = field(default_factory=dict)
    preprocessing_dir: str | None = None
    preprocessing_manifest_path: str | None = None
    preprocessing_manifest: dict[str, Any] = field(default_factory=dict)
    preprocessing_status: str | None = None
    preprocessing_cache_key: str | None = None
    preprocessing_reused_cache: bool = False
    audio_extraction_plan: dict[str, Any] = field(default_factory=dict)
    audio_targets: list[dict[str, Any]] = field(default_factory=list)
    frame_extraction_plan: dict[str, Any] = field(default_factory=dict)
    frame_targets: list[dict[str, Any]] = field(default_factory=list)

    preprocessing_cache_validation: dict[str, Any] = field(default_factory=dict)
    preprocessing_cache_validation_status: str | None = None
    preprocessing_cache_reuse_allowed: bool = False

    audio_extraction_result: dict[str, Any] = field(default_factory=dict)
    audio_extraction_status: str | None = None
    ready_audio_targets: list[str] = field(default_factory=list)
    missing_audio_targets: list[str] = field(default_factory=list)
    failed_audio_targets: list[str] = field(default_factory=list)

    transcript_report: dict[str, Any] = field(default_factory=dict)
    transcript_status: str | None = None
    transcript_source_path: str | None = None
    transcript_source_type: str | None = None
    transcript_segments: list[dict[str, Any]] = field(default_factory=list)
    transcript_text: str = ""
    transcript_segment_count: int = 0
    transcript_duration_seconds: float = 0.0
    transcript_language: str | None = None
    transcript_recommendation: str | None = None

    silence_detection_report: dict[str, Any] = field(default_factory=dict)
    silence_detection_result: dict[str, Any] = field(default_factory=dict)
    silence_detection_status: str | None = None
    silence_detection_source_path: str | None = None
    silence_detection_source_type: str | None = None
    silence_detection_threshold_db: float | None = None
    silence_detection_min_duration_seconds: float | None = None
    silence_segment_count: int = 0
    silence_total_seconds: float = 0.0

    silence_classification_report: dict[str, Any] = field(default_factory=dict)
    silence_classification_result: dict[str, Any] = field(default_factory=dict)
    silence_classification_status: str | None = None
    silence_classifications: list[dict[str, Any]] = field(default_factory=list)
    silence_classification_count: int = 0
    silence_remove_candidate_count: int = 0
    silence_keep_candidate_count: int = 0
    silence_counts_by_classification: dict[str, int] = field(default_factory=dict)

    rms_energy_report: dict[str, Any] = field(default_factory=dict)
    rms_energy_status: str | None = None
    rms_energy_source_selection: dict[str, Any] = field(default_factory=dict)
    rms_energy_timeline_result: dict[str, Any] = field(default_factory=dict)
    rms_energy_selected_path: str | None = None
    rms_energy_selected_type: str | None = None
    rms_energy_timeline_status: str | None = None
    rms_energy_point_count: int = 0
    rms_energy_duration_seconds: float = 0.0
    rms_energy_sample_rate: int | None = None
    rms_energy_channels: int | None = None
    rms_energy_frame_ms: float = 10.0
    rms_energy_hop_ms: float = 5.0
    rms_energy_min_rms: float = 0.0
    rms_energy_max_rms: float = 0.0
    rms_energy_avg_rms: float = 0.0
    rms_energy_min_normalized_energy: float = 0.0
    rms_energy_max_normalized_energy: float = 0.0
    rms_energy_avg_normalized_energy: float = 0.0
    rms_energy_context_adapter: dict[str, Any] = field(default_factory=dict)
    rms_energy_context_timeline: list[dict[str, Any]] = field(default_factory=list)
    rms_energy_context_status: str | None = None
    rms_energy_context_point_count: int = 0
    rms_energy_context_peak_count: int = 0
    rms_energy_context_silent_count: int = 0

    energy_peak_report: dict[str, Any] = field(default_factory=dict)
    energy_peak_status: str | None = None
    energy_peak_timeline_source: str | None = None
    energy_peak_detection_result: dict[str, Any] = field(default_factory=dict)
    energy_peaks: list[dict[str, Any]] = field(default_factory=list)
    energy_peak_count: int = 0
    energy_high_energy_peak_count: int = 0
    energy_local_max_peak_count: int = 0
    energy_rise_peak_count: int = 0
    energy_threshold_peak_count: int = 0
    energy_peak_threshold: float = 0.85
    energy_rise_threshold: float = 0.25
    energy_min_peak_distance_seconds: float = 0.4
    energy_max_peak_score: float = 0.0
    energy_avg_peak_score: float = 0.0
    energy_top_peak: dict[str, Any] = field(default_factory=dict)
    energy_peak_recommendation: str | None = None

    filler_word_report: dict[str, Any] = field(default_factory=dict)
    filler_word_status: str | None = None
    filler_word_transcript_source: str | None = None
    filler_word_detection_result: dict[str, Any] = field(default_factory=dict)
    filler_word_occurrences: list[dict[str, Any]] = field(default_factory=list)
    filler_word_occurrence_count: int = 0
    filler_word_remove_candidate_count: int = 0
    filler_word_counts_by_type: dict[str, int] = field(default_factory=dict)
    filler_word_counts_by_language: dict[str, int] = field(default_factory=dict)
    filler_word_total_duration_seconds: float = 0.0
    filler_word_transcript_word_count: int = 0
    filler_word_rate: float = 0.0
    filler_word_recommendation: str | None = None

    audio_normalization_report: dict[str, Any] = field(default_factory=dict)
    audio_normalization_status: str | None = None
    audio_normalization_selected_path: str | None = None
    audio_normalization_selected_type: str | None = None
    audio_normalization_source_selection: dict[str, Any] = field(default_factory=dict)
    audio_normalization_result: dict[str, Any] = field(default_factory=dict)
    audio_normalization_level_status: str | None = None
    audio_normalization_needed: bool = False
    audio_normalization_recommendation: str | None = None
    audio_normalization_target_rms_dbfs: float = -18.0
    audio_normalization_target_peak_dbfs: float = -1.0
    audio_normalization_recommended_gain_db: float = 0.0
    audio_normalization_limited_gain_db: float = 0.0
    audio_normalization_gain_limited_by_peak: bool = False
    audio_normalization_would_clip_after_gain: bool = False
    audio_normalization_peak_dbfs: float | None = None
    audio_normalization_rms_dbfs: float | None = None
    audio_normalization_peak_amplitude: float = 0.0
    audio_normalization_rms: float = 0.0
    audio_normalization_clipping_sample_count: int = 0
    audio_normalization_clipping_ratio: float = 0.0
    audio_normalization_sample_count: int = 0
    audio_normalization_duration_seconds: float = 0.0
    audio_normalization_sample_rate: int | None = None
    audio_normalization_channels: int | None = None

    beat_detection_report: dict[str, Any] = field(default_factory=dict)
    beat_detection_status: str | None = None
    beat_detection_selected_path: str | None = None
    beat_detection_selected_type: str | None = None
    beat_detection_source_selection: dict[str, Any] = field(default_factory=dict)
    beat_detection_result: dict[str, Any] = field(default_factory=dict)
    beat_detection_beats: list[dict[str, Any]] = field(default_factory=list)
    beat_detection_beat_count: int = 0
    beat_detection_estimated_bpm: float | None = None
    beat_detection_average_beat_interval_seconds: float | None = None
    beat_detection_duration_seconds: float = 0.0
    beat_detection_sample_rate: int | None = None
    beat_detection_channels: int | None = None
    beat_detection_energy_frame_count: int = 0
    beat_detection_peak_threshold: float = 1.35
    beat_detection_min_beat_distance_seconds: float = 0.25
    beat_detection_max_beat_strength: float = 0.0
    beat_detection_avg_beat_strength: float = 0.0
    beat_detection_top_beat: dict[str, Any] = field(default_factory=dict)
    beat_detection_recommendation: str | None = None

    recovery_status: str | None = None
    resume_safety: str | None = None
    recovery_report: dict[str, Any] = field(default_factory=dict)

    decision_log_path: str | None = None
    decision_jsonl_path: str | None = None
    error_log_path: str | None = None
    error_jsonl_path: str | None = None
    log_index: dict[str, Any] = field(default_factory=dict)

    debug_mode: str = "off"
    debug_context: dict[str, Any] = field(default_factory=dict)

    review_status: str = "pending"
    scheduled_at: Optional[str] = None
    is_scheduled: bool = False

    # 🔥 NEU (für Dashboard)
    is_rerender: bool = False
    source_job_id: str | None = None
    publish_status: str | None = None

    retry_count: int = 0
    max_retry_attempts: int | None = None
    retry_delay_minutes: int | None = None
    next_retry_at: str | None = None
    last_retry_at: str | None = None
    last_retry_reason: str | None = None
    retry_status: str | None = None
    permanently_failed: bool = False

    repost_requested: bool = False
    repost_count: int = 0
    last_repost_at: str | None = None
    next_repost_at: str | None = None
    repost_status: str | None = None 

    thumbnail_path: str | None = None
    video_path: str | None = None    
    render_version: int | None = None

    quality_score: float | None = None
    hook_score: float | None = None
    editing_score: float | None = None
    retention_potential_score: float | None = None
    shorts_potential_score: float | None = None
    final_score: float | None = None

    decision_reason: str | None = None
    improvement_hint: str | None = None

    recommended_action: str | None = None

    performance_tracking: dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "youtube_video_id": None,
        "last_synced_at": None,
        "metrics": {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "ctr": None,
            "average_view_duration": None,
            "average_percentage_viewed": None
        }
    })

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            job_id=data.get("job_id"),
            job_type=JobType(data.get("job_type", "gaming")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            target_format=TargetFormat(data.get("target_format", "short")),
            target_platforms=list(data.get("target_platforms", [])),
            status=JobStatus(data.get("status", "routed")),
            mode=Mode(data.get("mode", "normal")),
            autopublish_class=AutopublishClass(data.get("autopublish_class", "manual_only")),
            confidence_score=float(data.get("confidence_score", 0.0)),
            validator_status=ValidatorStatus(data.get("validator_status", "not_validated")),
            raw_video_path=data.get("raw_video_path"),
            topic=data.get("topic"),
            title=data.get("title"),            
            pipeline_type=PipelineType(data["pipeline_type"]) if data.get("pipeline_type") else None,
            profile_id=data.get("profile_id"),
            quality_mode=data.get("quality_mode"),
            profile_version=data.get("profile_version"),
            profile_snapshot_path=data.get("profile_snapshot_path"),
            profile_source=data.get("profile_source"),
            profile_metadata=dict(data.get("profile_metadata") or {}),
            state_history=list(data.get("state_history") or []),
            current_module=data.get("current_module"),
            error_message=data.get("error_message"),
            file_info=dict(data.get("file_info") or {}),
            file_acceptance=dict(data.get("file_acceptance") or {}),
            stream_classification=dict(data.get("stream_classification") or {}),
            file_readability=dict(data.get("file_readability") or {}),
            file_handler_report=dict(data.get("file_handler_report") or {}),
            preprocessing_dir=data.get("preprocessing_dir"),
            preprocessing_manifest_path=data.get("preprocessing_manifest_path"),
            preprocessing_manifest=dict(data.get("preprocessing_manifest") or {}),
            preprocessing_status=data.get("preprocessing_status"),
            preprocessing_cache_key=data.get("preprocessing_cache_key"),
            preprocessing_reused_cache=bool(data.get("preprocessing_reused_cache", False)),
            audio_extraction_plan=dict(data.get("audio_extraction_plan") or {}),
            audio_targets=list(data.get("audio_targets") or []),
            frame_extraction_plan=dict(data.get("frame_extraction_plan") or {}),
            frame_targets=list(data.get("frame_targets") or []),
            preprocessing_cache_validation=dict(data.get("preprocessing_cache_validation") or {}),
            preprocessing_cache_validation_status=data.get("preprocessing_cache_validation_status"),
            preprocessing_cache_reuse_allowed=bool(data.get("preprocessing_cache_reuse_allowed", False)),
            audio_extraction_result=dict(data.get("audio_extraction_result") or {}),
            audio_extraction_status=data.get("audio_extraction_status"),
            ready_audio_targets=list(data.get("ready_audio_targets") or []),
            missing_audio_targets=list(data.get("missing_audio_targets") or []),
            failed_audio_targets=list(data.get("failed_audio_targets") or []),
            transcript_report=dict(data.get("transcript_report") or {}),
            transcript_status=data.get("transcript_status"),
            transcript_source_path=data.get("transcript_source_path"),
            transcript_source_type=data.get("transcript_source_type"),
            transcript_segments=list(data.get("transcript_segments") or []),
            transcript_text=str(data.get("transcript_text") or ""),
            transcript_segment_count=int(data.get("transcript_segment_count", 0) or 0),
            transcript_duration_seconds=float(data.get("transcript_duration_seconds", 0.0) or 0.0),
            transcript_language=data.get("transcript_language"),
            transcript_recommendation=data.get("transcript_recommendation"),
            silence_detection_report=dict(data.get("silence_detection_report") or {}),
            silence_detection_result=dict(data.get("silence_detection_result") or {}),
            silence_detection_status=data.get("silence_detection_status"),
            silence_detection_source_path=data.get("silence_detection_source_path"),
            silence_detection_source_type=data.get("silence_detection_source_type"),
            silence_detection_threshold_db=(
                float(data["silence_detection_threshold_db"])
                if data.get("silence_detection_threshold_db") is not None
                else None
            ),
            silence_detection_min_duration_seconds=(
                float(data["silence_detection_min_duration_seconds"])
                if data.get("silence_detection_min_duration_seconds") is not None
                else None
            ),
            silence_segment_count=int(data.get("silence_segment_count", 0) or 0),
            silence_total_seconds=float(data.get("silence_total_seconds", 0.0) or 0.0),
            silence_classification_report=dict(data.get("silence_classification_report") or {}),
            silence_classification_result=dict(data.get("silence_classification_result") or {}),
            silence_classification_status=data.get("silence_classification_status"),
            silence_classifications=list(data.get("silence_classifications") or []),
            silence_classification_count=int(data.get("silence_classification_count", 0) or 0),
            silence_remove_candidate_count=int(data.get("silence_remove_candidate_count", 0) or 0),
            silence_keep_candidate_count=int(data.get("silence_keep_candidate_count", 0) or 0),
            silence_counts_by_classification=dict(data.get("silence_counts_by_classification") or {}),
            rms_energy_report=dict(data.get("rms_energy_report") or {}),
            rms_energy_status=data.get("rms_energy_status"),
            rms_energy_source_selection=dict(data.get("rms_energy_source_selection") or {}),
            rms_energy_timeline_result=dict(data.get("rms_energy_timeline_result") or {}),
            rms_energy_selected_path=data.get("rms_energy_selected_path"),
            rms_energy_selected_type=data.get("rms_energy_selected_type"),
            rms_energy_timeline_status=data.get("rms_energy_timeline_status"),
            rms_energy_point_count=int(data.get("rms_energy_point_count", 0) or 0),
            rms_energy_duration_seconds=float(data.get("rms_energy_duration_seconds", 0.0) or 0.0),
            rms_energy_sample_rate=(
                int(data["rms_energy_sample_rate"])
                if data.get("rms_energy_sample_rate") is not None
                else None
            ),
            rms_energy_channels=(
                int(data["rms_energy_channels"])
                if data.get("rms_energy_channels") is not None
                else None
            ),
            rms_energy_frame_ms=float(data.get("rms_energy_frame_ms", 10.0) or 10.0),
            rms_energy_hop_ms=float(data.get("rms_energy_hop_ms", 5.0) or 5.0),
            rms_energy_min_rms=float(data.get("rms_energy_min_rms", 0.0) or 0.0),
            rms_energy_max_rms=float(data.get("rms_energy_max_rms", 0.0) or 0.0),
            rms_energy_avg_rms=float(data.get("rms_energy_avg_rms", 0.0) or 0.0),
            rms_energy_min_normalized_energy=float(data.get("rms_energy_min_normalized_energy", 0.0) or 0.0),
            rms_energy_max_normalized_energy=float(data.get("rms_energy_max_normalized_energy", 0.0) or 0.0),
            rms_energy_avg_normalized_energy=float(data.get("rms_energy_avg_normalized_energy", 0.0) or 0.0),
            rms_energy_context_adapter=dict(data.get("rms_energy_context_adapter") or {}),
            rms_energy_context_timeline=list(data.get("rms_energy_context_timeline") or []),
            rms_energy_context_status=data.get("rms_energy_context_status"),
            rms_energy_context_point_count=int(data.get("rms_energy_context_point_count", 0) or 0),
            rms_energy_context_peak_count=int(data.get("rms_energy_context_peak_count", 0) or 0),
            rms_energy_context_silent_count=int(data.get("rms_energy_context_silent_count", 0) or 0),
            energy_peak_report=dict(data.get("energy_peak_report") or {}),
            energy_peak_status=data.get("energy_peak_status"),
            energy_peak_timeline_source=data.get("energy_peak_timeline_source"),
            energy_peak_detection_result=dict(data.get("energy_peak_detection_result") or {}),
            energy_peaks=list(data.get("energy_peaks") or []),
            energy_peak_count=int(data.get("energy_peak_count", 0) or 0),
            energy_high_energy_peak_count=int(data.get("energy_high_energy_peak_count", 0) or 0),
            energy_local_max_peak_count=int(data.get("energy_local_max_peak_count", 0) or 0),
            energy_rise_peak_count=int(data.get("energy_rise_peak_count", 0) or 0),
            energy_threshold_peak_count=int(data.get("energy_threshold_peak_count", 0) or 0),
            energy_peak_threshold=float(data.get("energy_peak_threshold", 0.85) or 0.85),
            energy_rise_threshold=float(data.get("energy_rise_threshold", 0.25) or 0.25),
            energy_min_peak_distance_seconds=float(data.get("energy_min_peak_distance_seconds", 0.4) or 0.4),
            energy_max_peak_score=float(data.get("energy_max_peak_score", 0.0) or 0.0),
            energy_avg_peak_score=float(data.get("energy_avg_peak_score", 0.0) or 0.0),
            energy_top_peak=dict(data.get("energy_top_peak") or {}),
            energy_peak_recommendation=data.get("energy_peak_recommendation"),
            filler_word_report=dict(data.get("filler_word_report") or {}),
            filler_word_status=data.get("filler_word_status"),
            filler_word_transcript_source=data.get("filler_word_transcript_source"),
            filler_word_detection_result=dict(data.get("filler_word_detection_result") or {}),
            filler_word_occurrences=list(data.get("filler_word_occurrences") or []),
            filler_word_occurrence_count=int(data.get("filler_word_occurrence_count", 0) or 0),
            filler_word_remove_candidate_count=int(data.get("filler_word_remove_candidate_count", 0) or 0),
            filler_word_counts_by_type={
                str(k): int(v) for k, v in (data.get("filler_word_counts_by_type") or {}).items()
            } if isinstance(data.get("filler_word_counts_by_type"), dict) else {},
            filler_word_counts_by_language={
                str(k): int(v) for k, v in (data.get("filler_word_counts_by_language") or {}).items()
            } if isinstance(data.get("filler_word_counts_by_language"), dict) else {},
            filler_word_total_duration_seconds=float(data.get("filler_word_total_duration_seconds", 0.0) or 0.0),
            filler_word_transcript_word_count=int(data.get("filler_word_transcript_word_count", 0) or 0),
            filler_word_rate=float(data.get("filler_word_rate", 0.0) or 0.0),
            filler_word_recommendation=data.get("filler_word_recommendation"),
            audio_normalization_report=dict(data.get("audio_normalization_report") or {}),
            audio_normalization_status=data.get("audio_normalization_status"),
            audio_normalization_selected_path=data.get("audio_normalization_selected_path"),
            audio_normalization_selected_type=data.get("audio_normalization_selected_type"),
            audio_normalization_source_selection=dict(data.get("audio_normalization_source_selection") or {}),
            audio_normalization_result=dict(data.get("audio_normalization_result") or {}),
            audio_normalization_level_status=data.get("audio_normalization_level_status"),
            audio_normalization_needed=bool(data.get("audio_normalization_needed", False)),
            audio_normalization_recommendation=data.get("audio_normalization_recommendation"),
            audio_normalization_target_rms_dbfs=float(data.get("audio_normalization_target_rms_dbfs", -18.0) or -18.0),
            audio_normalization_target_peak_dbfs=float(data.get("audio_normalization_target_peak_dbfs", -1.0) or -1.0),
            audio_normalization_recommended_gain_db=float(data.get("audio_normalization_recommended_gain_db", 0.0) or 0.0),
            audio_normalization_limited_gain_db=float(data.get("audio_normalization_limited_gain_db", 0.0) or 0.0),
            audio_normalization_gain_limited_by_peak=bool(data.get("audio_normalization_gain_limited_by_peak", False)),
            audio_normalization_would_clip_after_gain=bool(data.get("audio_normalization_would_clip_after_gain", False)),
            audio_normalization_peak_dbfs=(
                float(data["audio_normalization_peak_dbfs"])
                if data.get("audio_normalization_peak_dbfs") is not None
                else None
            ),
            audio_normalization_rms_dbfs=(
                float(data["audio_normalization_rms_dbfs"])
                if data.get("audio_normalization_rms_dbfs") is not None
                else None
            ),
            audio_normalization_peak_amplitude=float(data.get("audio_normalization_peak_amplitude", 0.0) or 0.0),
            audio_normalization_rms=float(data.get("audio_normalization_rms", 0.0) or 0.0),
            audio_normalization_clipping_sample_count=int(data.get("audio_normalization_clipping_sample_count", 0) or 0),
            audio_normalization_clipping_ratio=float(data.get("audio_normalization_clipping_ratio", 0.0) or 0.0),
            audio_normalization_sample_count=int(data.get("audio_normalization_sample_count", 0) or 0),
            audio_normalization_duration_seconds=float(data.get("audio_normalization_duration_seconds", 0.0) or 0.0),
            audio_normalization_sample_rate=(
                int(data["audio_normalization_sample_rate"])
                if data.get("audio_normalization_sample_rate") is not None
                else None
            ),
            audio_normalization_channels=(
                int(data["audio_normalization_channels"])
                if data.get("audio_normalization_channels") is not None
                else None
            ),
            beat_detection_report=dict(data.get("beat_detection_report") or {}),
            beat_detection_status=data.get("beat_detection_status"),
            beat_detection_selected_path=data.get("beat_detection_selected_path"),
            beat_detection_selected_type=data.get("beat_detection_selected_type"),
            beat_detection_source_selection=dict(data.get("beat_detection_source_selection") or {}),
            beat_detection_result=dict(data.get("beat_detection_result") or {}),
            beat_detection_beats=list(data.get("beat_detection_beats") or []),
            beat_detection_beat_count=int(data.get("beat_detection_beat_count", 0) or 0),
            beat_detection_estimated_bpm=(
                float(data["beat_detection_estimated_bpm"])
                if data.get("beat_detection_estimated_bpm") is not None
                else None
            ),
            beat_detection_average_beat_interval_seconds=(
                float(data["beat_detection_average_beat_interval_seconds"])
                if data.get("beat_detection_average_beat_interval_seconds") is not None
                else None
            ),
            beat_detection_duration_seconds=float(data.get("beat_detection_duration_seconds", 0.0) or 0.0),
            beat_detection_sample_rate=(
                int(data["beat_detection_sample_rate"])
                if data.get("beat_detection_sample_rate") is not None
                else None
            ),
            beat_detection_channels=(
                int(data["beat_detection_channels"])
                if data.get("beat_detection_channels") is not None
                else None
            ),
            beat_detection_energy_frame_count=int(data.get("beat_detection_energy_frame_count", 0) or 0),
            beat_detection_peak_threshold=float(data.get("beat_detection_peak_threshold", 1.35) or 1.35),
            beat_detection_min_beat_distance_seconds=float(
                data.get("beat_detection_min_beat_distance_seconds", 0.25) or 0.25
            ),
            beat_detection_max_beat_strength=float(data.get("beat_detection_max_beat_strength", 0.0) or 0.0),
            beat_detection_avg_beat_strength=float(data.get("beat_detection_avg_beat_strength", 0.0) or 0.0),
            beat_detection_top_beat=dict(data.get("beat_detection_top_beat") or {}),
            beat_detection_recommendation=data.get("beat_detection_recommendation"),
            recovery_status=data.get("recovery_status"),
            resume_safety=data.get("resume_safety"),
            recovery_report=dict(data.get("recovery_report") or {}),
            decision_log_path=data.get("decision_log_path"),
            decision_jsonl_path=data.get("decision_jsonl_path"),
            error_log_path=data.get("error_log_path"),
            error_jsonl_path=data.get("error_jsonl_path"),
            log_index=dict(data.get("log_index") or {}),
            debug_mode=data.get("debug_mode", "off"),
            debug_context=dict(data.get("debug_context") or {}),
            review_status=data.get("review_status", "pending"),
            scheduled_at=data.get("scheduled_at"),
            is_scheduled=data.get("is_scheduled", False),

            # 🔥 NEU
            is_rerender=bool(
    data.get("is_rerender", False) or data.get("rerender_requested", False)
),
            source_job_id=data.get("source_job_id"),
            publish_status=data.get("publish_status"),

            retry_count=int(data.get("retry_count", 0)),
            max_retry_attempts=(
                int(data["max_retry_attempts"])
                if data.get("max_retry_attempts") is not None
                else None
            ),
            retry_delay_minutes=(
                int(data["retry_delay_minutes"])
                if data.get("retry_delay_minutes") is not None
                else None
            ),
            next_retry_at=data.get("next_retry_at"),
            last_retry_at=data.get("last_retry_at"),
            last_retry_reason=data.get("last_retry_reason"),
            retry_status=data.get("retry_status"),
            permanently_failed=bool(data.get("permanently_failed", False)),
            repost_requested=bool(data.get("repost_requested", False)),
            repost_count=int(data.get("repost_count", 0)),
            last_repost_at=data.get("last_repost_at"),
            next_repost_at=data.get("next_repost_at"),
            repost_status=data.get("repost_status"),

thumbnail_path=data.get("thumbnail_path"),
video_path=data.get("video_path"),
render_version=(
    int(data["render_version"])
    if data.get("render_version") is not None
    else None
),
shorts=[
    {
        "short_id": (
            short.get("short_id")
            if isinstance(short, dict) and short.get("short_id")
            else f"short_{index}"
        ),
        "path": (
            short.get("path")
            if isinstance(short, dict)
            else short
        ),
        "status": (
            short.get("status")
            if isinstance(short, dict) and short.get("status")
            else "generated"
        ),
        "review_status": (
            short.get("review_status")
            if isinstance(short, dict) and short.get("review_status")
            else "pending"
        ),
        "publish_status": (
            short.get("publish_status")
            if isinstance(short, dict) and short.get("publish_status")
            else "not_published"
        ),

        "retry_count": (
            int(short.get("retry_count", 0))
            if isinstance(short, dict)
            else 0
        ),
        "max_retry_attempts": (
            int(short["max_retry_attempts"])
            if isinstance(short, dict) and short.get("max_retry_attempts") is not None
            else None
        ),
        "retry_delay_minutes": (
            int(short["retry_delay_minutes"])
            if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
            else None
        ),
        "next_retry_at": (
            short.get("next_retry_at")
            if isinstance(short, dict)
            else None
        ),
        "last_retry_at": (
            short.get("last_retry_at")
            if isinstance(short, dict)
            else None
        ),
        "last_retry_reason": (
            short.get("last_retry_reason")
            if isinstance(short, dict)
            else None
        ),
        "retry_status": (
            short.get("retry_status")
            if isinstance(short, dict)
            else None
        ),
        "permanently_failed": (
            bool(short.get("permanently_failed", False))
            if isinstance(short, dict)
            else False
        ),
        "platform_targets": (
            list(short.get("platform_targets"))
            if isinstance(short, dict) and short.get("platform_targets")
            else []
        ),
        "segment": (
            {
                "label": short["segment"].get("label"),
                "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                "score": float(short["segment"].get("score", 0.0)),
                "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
            }
            if isinstance(short, dict) and isinstance(short.get("segment"), dict)
            else None
        ),
    }
    for index, short in enumerate(data.get("shorts", []), start=1)
    if ((short.get("path") if isinstance(short, dict) else short))
],

            quality_score=float(data["quality_score"]) if data.get("quality_score") is not None else None,
            hook_score=float(data["hook_score"]) if data.get("hook_score") is not None else None,
            editing_score=float(data["editing_score"]) if data.get("editing_score") is not None else None,
            retention_potential_score=float(data["retention_potential_score"]) if data.get("retention_potential_score") is not None else None,
            shorts_potential_score=float(data["shorts_potential_score"]) if data.get("shorts_potential_score") is not None else None,
            final_score=float(data["final_score"]) if data.get("final_score") is not None else None,
            decision_reason=data.get("decision_reason"),
            improvement_hint=data.get("improvement_hint"),

            recommended_action=data.get("recommended_action"),

            performance_tracking=data.get("performance_tracking", {
                "enabled": True,
                "youtube_video_id": None,
                "last_synced_at": None,
                "metrics": {
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "ctr": None,
                    "average_view_duration": None,
                    "average_percentage_viewed": None
                }
            }),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
