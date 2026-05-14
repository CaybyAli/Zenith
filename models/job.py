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
    transcript_normalized_segment_count: int = 0
    transcript_valid_segment_count: int = 0
    transcript_invalid_segment_count: int = 0
    transcript_word_count: int = 0
    transcript_normalized_word_count: int = 0
    transcript_word_timestamp_count: int = 0
    transcript_has_word_level_timestamps: bool = False
    transcript_segment_normalization_status: str | None = None
    transcript_segment_normalization_recommendation: str | None = None

    sentence_boundary_report: dict[str, Any] = field(default_factory=dict)
    sentence_boundary_status: str | None = None
    sentence_boundary_boundaries: list[dict[str, Any]] = field(default_factory=list)
    sentence_boundary_protection_zones: list[dict[str, Any]] = field(default_factory=list)
    sentence_boundary_boundary_count: int = 0
    sentence_boundary_protection_zone_count: int = 0
    sentence_boundary_complete_sentence_count: int = 0
    sentence_boundary_open_fragment_count: int = 0
    sentence_boundary_question_count: int = 0
    sentence_boundary_open_question_count: int = 0
    sentence_boundary_safe_boundary_count: int = 0
    sentence_boundary_unsafe_boundary_count: int = 0
    sentence_boundary_recommendation: str | None = None

    keyword_emotion_report: dict[str, Any] = field(default_factory=dict)
    keyword_emotion_status: str | None = None
    keyword_emotion_matches: list[dict[str, Any]] = field(default_factory=list)
    keyword_emotion_segment_scores: list[dict[str, Any]] = field(default_factory=list)
    keyword_emotion_match_count: int = 0
    keyword_emotion_segment_score_count: int = 0
    keyword_emotion_hype_match_count: int = 0
    keyword_emotion_frustration_match_count: int = 0
    keyword_emotion_shock_match_count: int = 0
    keyword_emotion_laugh_match_count: int = 0
    keyword_emotion_question_match_count: int = 0
    keyword_emotion_high_value_segment_count: int = 0
    keyword_emotion_recommendation: str | None = None

    interaction_classification_report: dict[str, Any] = field(default_factory=dict)
    interaction_classification_status: str | None = None
    interaction_classification_points: list[dict[str, Any]] = field(default_factory=list)
    interaction_classification_segments: list[dict[str, Any]] = field(default_factory=list)
    interaction_classification_point_count: int = 0
    interaction_classification_segment_count: int = 0
    interaction_classification_monologue_count: int = 0
    interaction_classification_interaction_count: int = 0
    interaction_classification_question_answer_count: int = 0
    interaction_classification_chat_reaction_count: int = 0
    interaction_classification_callout_count: int = 0
    interaction_classification_commentary_count: int = 0
    interaction_classification_private_or_meta_count: int = 0
    interaction_classification_context_needed_count: int = 0
    interaction_classification_recommendation: str | None = None

    dead_content_report: dict[str, Any] = field(default_factory=dict)
    dead_content_status: str | None = None
    dead_content_candidates: list[dict[str, Any]] = field(default_factory=list)
    dead_content_segment_scores: list[dict[str, Any]] = field(default_factory=list)
    dead_content_candidate_count: int = 0
    dead_content_segment_score_count: int = 0
    dead_content_dead_air_candidate_count: int = 0
    dead_content_low_value_candidate_count: int = 0
    dead_content_filler_pause_candidate_count: int = 0
    dead_content_loading_or_menu_candidate_count: int = 0
    dead_content_private_or_meta_candidate_count: int = 0
    dead_content_protected_candidate_count: int = 0
    dead_content_high_confidence_candidate_count: int = 0
    dead_content_recommendation: str | None = None

    content_value_report: dict[str, Any] = field(default_factory=dict)
    content_value_status: str | None = None
    content_value_segment_scores: list[dict[str, Any]] = field(default_factory=list)
    content_value_segment_score_count: int = 0
    content_value_high_value_count: int = 0
    content_value_mid_value_count: int = 0
    content_value_low_value_count: int = 0
    content_value_protected_context_count: int = 0
    content_value_hook_candidate_count: int = 0
    content_value_technical_warning_count: int = 0
    content_value_avg_score: float = 0.0
    content_value_max_score: float = 0.0
    content_value_min_score: float = 0.0
    content_value_recommendation: str | None = None

    profanity_censor_report: dict[str, Any] = field(default_factory=dict)
    profanity_censor_status: str | None = None
    profanity_censor_matches: list[dict[str, Any]] = field(default_factory=list)
    profanity_censor_segment_results: list[dict[str, Any]] = field(default_factory=list)
    profanity_censor_match_count: int = 0
    profanity_censor_severe_match_count: int = 0
    profanity_censor_mild_match_count: int = 0
    profanity_censor_required_count: int = 0
    profanity_censor_word_level_match_count: int = 0
    profanity_censor_segment_fallback_match_count: int = 0
    profanity_censor_recommendation: str | None = None

    unified_edit_signal_report: dict[str, Any] = field(default_factory=dict)
    unified_edit_signal_status: str | None = None
    unified_edit_signals: list[dict[str, Any]] = field(default_factory=list)
    unified_edit_signal_count: int = 0
    unified_edit_signal_summary: dict[str, Any] = field(default_factory=dict)
    unified_edit_signal_recommendation: str | None = None
    segment_classification_report: dict[str, Any] = field(default_factory=dict)
    segment_classification_status: str | None = None
    segment_classification_segments: list[dict[str, Any]] = field(default_factory=list)
    segment_classification_segment_count: int = 0
    segment_classification_highlight_count: int = 0
    segment_classification_hook_candidate_count: int = 0
    segment_classification_protected_context_count: int = 0
    segment_classification_dead_candidate_count: int = 0
    segment_classification_filler_count: int = 0
    segment_classification_transition_count: int = 0
    segment_classification_censor_required_count: int = 0
    segment_classification_technical_warning_count: int = 0
    segment_classification_recommendation: str | None = None
    murch_scoring_report: dict[str, Any] = field(default_factory=dict)
    murch_scoring_status: str | None = None
    murch_scoring_segment_scores: list[dict[str, Any]] = field(default_factory=list)
    murch_scoring_segment_score_count: int = 0
    murch_scoring_high_score_count: int = 0
    murch_scoring_medium_score_count: int = 0
    murch_scoring_low_score_count: int = 0
    murch_scoring_protected_context_count: int = 0
    murch_scoring_censor_required_count: int = 0
    murch_scoring_technical_warning_count: int = 0
    murch_scoring_avg_score: float = 0.0
    murch_scoring_max_score: float = 0.0
    murch_scoring_min_score: float = 0.0
    murch_scoring_recommendation: str | None = None
 
    cut_list_report: dict[str, Any] = field(default_factory=dict)
    cut_list_status: str | None = None
    cut_list_items: list[dict[str, Any]] = field(default_factory=list)
    cut_list_item_count: int = 0
    cut_list_keep_count: int = 0
    cut_list_review_keep_count: int = 0
    cut_list_review_trim_count: int = 0
    cut_list_review_remove_count: int = 0
    cut_list_protect_count: int = 0
    cut_list_censor_keep_count: int = 0
    cut_list_technical_review_count: int = 0
    cut_list_unknown_review_count: int = 0
    cut_list_recommendation: str | None = None

    clip_duration_report: dict[str, Any] = field(default_factory=dict)
    clip_duration_status: str | None = None
    clip_duration_recommendations: list[dict[str, Any]] = field(default_factory=list)
    clip_duration_recommendation_count: int = 0
    clip_duration_ok_count: int = 0
    clip_duration_too_short_count: int = 0
    clip_duration_too_long_count: int = 0
    clip_duration_trim_review_count: int = 0
    clip_duration_extend_review_count: int = 0
    clip_duration_protect_duration_count: int = 0
    clip_duration_censor_keep_count: int = 0
    clip_duration_technical_review_count: int = 0
    clip_duration_invalid_timing_count: int = 0
    clip_duration_recommendation: str | None = None
    transition_decision_report: dict[str, Any] = field(default_factory=dict)
    transition_decision_status: str | None = None
    transition_decision_decisions: list[dict[str, Any]] = field(default_factory=list)
    transition_decision_count: int = 0
    transition_decision_hard_cut_review_count: int = 0
    transition_decision_j_cut_review_count: int = 0
    transition_decision_l_cut_review_count: int = 0
    transition_decision_quick_fade_review_count: int = 0
    transition_decision_no_cut_protect_count: int = 0
    transition_decision_censor_safe_keep_count: int = 0
    transition_decision_technical_review_count: int = 0
    transition_decision_unknown_review_count: int = 0
    transition_decision_recommendation: str | None = None
    continuity_check_report: dict[str, Any] = field(default_factory=dict)
    continuity_check_status: str | None = None
    continuity_check_issues: list[dict[str, Any]] = field(default_factory=list)
    continuity_check_issue_count: int = 0
    continuity_check_blocking_issue_count: int = 0
    continuity_check_sentence_break_risk_count: int = 0
    continuity_check_context_jump_risk_count: int = 0
    continuity_check_censor_context_risk_count: int = 0
    continuity_check_timing_issue_count: int = 0
    continuity_check_transition_conflict_count: int = 0
    continuity_check_technical_issue_count: int = 0
    continuity_check_protected_context_count: int = 0
    continuity_check_recommendation: str | None = None
    final_cut_list_report: dict[str, Any] = field(default_factory=dict)
    final_cut_list_status: str | None = None
    final_cut_list_items: list[dict[str, Any]] = field(default_factory=list)
    final_cut_list_item_count: int = 0
    final_cut_list_keep_review_count: int = 0
    final_cut_list_keep_high_value_count: int = 0
    final_cut_list_trim_review_count: int = 0
    final_cut_list_remove_review_count: int = 0
    final_cut_list_protect_count: int = 0
    final_cut_list_censor_keep_count: int = 0
    final_cut_list_technical_review_count: int = 0
    final_cut_list_blocked_by_continuity_count: int = 0
    final_cut_list_unknown_review_count: int = 0
    final_cut_list_review_required_count: int = 0
    final_cut_list_blocking_issue_count: int = 0
    final_cut_list_recommendation: str | None = None
    review_timeline_plan_report: dict[str, Any] = field(default_factory=dict)
    review_timeline_plan: dict[str, Any] = field(default_factory=dict)
    review_timeline_plan_status: str | None = None
    review_timeline_plan_id: str | None = None
    review_timeline_plan_items: list[dict[str, Any]] = field(default_factory=list)
    review_timeline_plan_item_count: int = 0
    review_timeline_plan_total_duration_seconds: float = 0.0
    review_timeline_plan_review_required_count: int = 0
    review_timeline_plan_protected_count: int = 0
    review_timeline_plan_censor_required_count: int = 0
    review_timeline_plan_continuity_blocked_count: int = 0
    review_timeline_plan_recommendation: str | None = None

    timeline_approval_gate_report: dict[str, Any] = field(default_factory=dict)
    timeline_approval_gate: dict[str, Any] = field(default_factory=dict)
    timeline_approval_gate_status: str | None = None
    timeline_approval_gate_id: str | None = None
    timeline_approval_status: str | None = None
    timeline_approval_requested_status: str | None = None
    timeline_approved_by: str | None = None
    timeline_rejected_by: str | None = None
    timeline_manual_change_reason: str | None = None
    timeline_can_proceed_to_execution: bool = False
    timeline_can_render: bool = False
    timeline_requires_human_approval: bool = True
    timeline_approval_blocking_reasons: list[str] = field(default_factory=list)
    timeline_approval_warnings: list[str] = field(default_factory=list)

    timeline_safety_validator_report: dict[str, Any] = field(default_factory=dict)
    timeline_safety_validator: dict[str, Any] = field(default_factory=dict)
    timeline_safety_validation_id: str | None = None
    timeline_safety_validation_status: str | None = None
    timeline_is_safe_for_future_execution: bool = False
    timeline_is_safe_for_render: bool = False
    timeline_safety_requires_manual_review: bool = True
    timeline_safety_blocking_errors: list[str] = field(default_factory=list)
    timeline_safety_warnings: list[str] = field(default_factory=list)
    timeline_safety_item_results: list[dict[str, Any]] = field(default_factory=list)
    timeline_safety_invalid_timing_count: int = 0
    timeline_safety_overlap_count: int = 0
    timeline_safety_gap_count: int = 0
    timeline_safety_protected_violation_count: int = 0
    timeline_safety_censor_violation_count: int = 0
    timeline_safety_continuity_violation_count: int = 0
    timeline_safety_approval_violation_count: int = 0
    review_timeline_dashboard_package_report: dict[str, Any] = field(default_factory=dict)
    review_timeline_dashboard_package: dict[str, Any] = field(default_factory=dict)
    review_timeline_dashboard_package_id: str | None = None
    review_timeline_dashboard_package_status: str | None = None

    review_timeline_dashboard_review_status: str | None = None
    review_timeline_dashboard_approval_status: str | None = None
    review_timeline_dashboard_safety_status: str | None = None

    review_timeline_dashboard_can_proceed_to_execution: bool = False
    review_timeline_dashboard_can_render: bool = False
    review_timeline_dashboard_requires_manual_review: bool = True

    review_timeline_dashboard_is_safe_for_future_execution: bool = False
    review_timeline_dashboard_is_safe_for_render: bool = False

    review_timeline_dashboard_summary: dict[str, Any] = field(default_factory=dict)
    review_timeline_dashboard_counters: dict[str, Any] = field(default_factory=dict)
    review_timeline_dashboard_item_cards: list[dict[str, Any]] = field(default_factory=list)
    review_timeline_dashboard_approval_panel: dict[str, Any] = field(default_factory=dict)
    review_timeline_dashboard_safety_panel: dict[str, Any] = field(default_factory=dict)

    review_timeline_dashboard_warnings: list[str] = field(default_factory=list)
    review_timeline_dashboard_blocking_errors: list[str] = field(default_factory=list)
    review_timeline_dashboard_actions: list[str] = field(default_factory=list)

    hook_identification_report: dict[str, Any] = field(default_factory=dict)
    hook_identification: dict[str, Any] = field(default_factory=dict)
    hook_identification_status: str | None = None
    hook_candidates: list[dict[str, Any]] = field(default_factory=list)
    hook_selected_candidate: dict[str, Any] | None = None
    hook_best_score: float = 0.0
    hook_review_required: bool = True
    hook_can_apply: bool = False
    hook_can_reorder_timeline: bool = False
    hook_can_render: bool = False
    hook_blocking_reasons: list[str] = field(default_factory=list)
    hook_warnings: list[str] = field(default_factory=list)
    hook_recommendation: str | None = None

    emotional_arc_report: dict[str, Any] = field(default_factory=dict)
    emotional_arc: dict[str, Any] = field(default_factory=dict)
    emotional_arc_status: str | None = None
    emotional_arc_points: list[dict[str, Any]] = field(default_factory=list)
    emotional_arc_suggestions: list[dict[str, Any]] = field(default_factory=list)
    emotional_arc_average_deviation: float = 0.0
    emotional_arc_max_deviation: float = 0.0
    emotional_arc_flatness_score: float = 0.0
    emotional_arc_hook_strength_score: float = 0.0
    emotional_arc_climax_strength_score: float = 0.0
    emotional_arc_breathing_room_score: float = 0.0
    emotional_arc_review_required: bool = True
    emotional_arc_can_apply: bool = False
    emotional_arc_can_reorder_timeline: bool = False
    emotional_arc_can_trim: bool = False
    emotional_arc_can_extend: bool = False
    emotional_arc_can_render: bool = False
    emotional_arc_blocking_reasons: list[str] = field(default_factory=list)
    emotional_arc_warnings: list[str] = field(default_factory=list)
    emotional_arc_recommendation: str | None = None

    dynamic_pacing_report: dict[str, Any] = field(default_factory=dict)
    dynamic_pacing: dict[str, Any] = field(default_factory=dict)
    dynamic_pacing_status: str | None = None
    dynamic_pacing_segments: list[dict[str, Any]] = field(default_factory=list)
    dynamic_pacing_suggestions: list[dict[str, Any]] = field(default_factory=list)
    dynamic_pacing_average_cut_rate: float = 0.0
    dynamic_pacing_target_cut_rate_range: dict[str, Any] = field(default_factory=dict)
    dynamic_pacing_match_score: float = 0.0
    dynamic_pacing_monotony_score: float = 0.0
    dynamic_pacing_breathing_room_score: float = 0.0
    dynamic_pacing_fast_run_count: int = 0
    dynamic_pacing_slow_run_count: int = 0
    dynamic_pacing_review_required: bool = True
    dynamic_pacing_can_apply: bool = False
    dynamic_pacing_can_split_clips: bool = False
    dynamic_pacing_can_merge_clips: bool = False
    dynamic_pacing_can_trim: bool = False
    dynamic_pacing_can_extend: bool = False
    dynamic_pacing_can_reorder_timeline: bool = False
    dynamic_pacing_can_render: bool = False
    dynamic_pacing_blocking_reasons: list[str] = field(default_factory=list)
    dynamic_pacing_warnings: list[str] = field(default_factory=list)
    dynamic_pacing_recommendation: str | None = None

    pattern_interrupt_report: dict[str, Any] = field(default_factory=dict)
    pattern_interrupt: dict[str, Any] = field(default_factory=dict)
    pattern_interrupt_status: str | None = None
    pattern_interrupt_windows: list[dict[str, Any]] = field(default_factory=list)
    pattern_interrupt_suggestions: list[dict[str, Any]] = field(default_factory=list)
    pattern_interrupt_total_windows: int = 0
    pattern_interrupt_needed_count: int = 0
    pattern_interrupt_monotony_score: float = 0.0
    pattern_interrupt_average_window_duration_seconds: float = 0.0
    pattern_interrupt_recommended_count: int = 0
    pattern_interrupt_review_required: bool = True
    pattern_interrupt_can_apply: bool = False
    pattern_interrupt_can_insert_zoom: bool = False
    pattern_interrupt_can_insert_text_overlay: bool = False
    pattern_interrupt_can_insert_sfx: bool = False
    pattern_interrupt_can_reorder_timeline: bool = False
    pattern_interrupt_can_trim: bool = False
    pattern_interrupt_can_extend: bool = False
    pattern_interrupt_can_render: bool = False
    pattern_interrupt_blocking_reasons: list[str] = field(default_factory=list)
    pattern_interrupt_warnings: list[str] = field(default_factory=list)
    pattern_interrupt_recommendation: str | None = None

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

    scene_change_report: dict[str, Any] = field(default_factory=dict)
    scene_change_status: str | None = None
    scene_change_selected_path: str | None = None
    scene_change_selected_type: str | None = None
    scene_change_result: dict[str, Any] = field(default_factory=dict)
    scene_changes: list[dict[str, Any]] = field(default_factory=list)
    scene_change_count: int = 0
    scene_change_hard_count: int = 0
    scene_change_soft_count: int = 0
    scene_change_false_positive_candidate_count: int = 0
    scene_change_threshold: float = 0.30
    scene_change_duration_seconds: float | None = None
    scene_change_recommendation: str | None = None
    motion_analysis_report: dict[str, Any] = field(default_factory=dict)
    motion_analysis_status: str | None = None
    motion_analysis_selected_path: str | None = None
    motion_analysis_selected_type: str | None = None
    motion_analysis_result: dict[str, Any] = field(default_factory=dict)
    motion_analysis_points: list[dict[str, Any]] = field(default_factory=list)
    motion_analysis_segments: list[dict[str, Any]] = field(default_factory=list)
    motion_analysis_point_count: int = 0
    motion_analysis_segment_count: int = 0
    motion_analysis_low_motion_segment_count: int = 0
    motion_analysis_high_motion_segment_count: int = 0
    motion_analysis_dead_visual_candidate_count: int = 0
    motion_analysis_duration_seconds: float | None = None
    motion_analysis_frame_sample_rate: float = 2.0
    motion_analysis_recommendation: str | None = None
    face_reaction_report: dict[str, Any] = field(default_factory=dict)
    face_reaction_status: str | None = None
    face_reaction_selected_path: str | None = None
    face_reaction_selected_type: str | None = None
    face_reaction_result: dict[str, Any] = field(default_factory=dict)
    face_reaction_points: list[dict[str, Any]] = field(default_factory=list)
    face_reaction_segments: list[dict[str, Any]] = field(default_factory=list)
    face_reaction_point_count: int = 0
    face_reaction_segment_count: int = 0
    face_reaction_detected_point_count: int = 0
    face_reaction_candidate_count: int = 0
    face_reaction_high_segment_count: int = 0
    face_reaction_duration_seconds: float | None = None
    face_reaction_frame_sample_rate: float = 2.0
    face_reaction_recommendation: str | None = None
    stutter_detection_report: dict[str, Any] = field(default_factory=dict)
    stutter_detection_status: str | None = None
    stutter_detection_selected_path: str | None = None
    stutter_detection_selected_type: str | None = None
    stutter_detection_result: dict[str, Any] = field(default_factory=dict)
    stutter_detection_points: list[dict[str, Any]] = field(default_factory=list)
    stutter_detection_segments: list[dict[str, Any]] = field(default_factory=list)
    stutter_detection_point_count: int = 0
    stutter_detection_segment_count: int = 0
    stutter_detection_duplicate_candidate_count: int = 0
    stutter_detection_stutter_segment_count: int = 0
    stutter_detection_freeze_segment_count: int = 0
    stutter_detection_duration_seconds: float | None = None
    stutter_detection_frame_sample_rate: float = 10.0
    stutter_detection_recommendation: str | None = None
    screen_content_report: dict[str, Any] = field(default_factory=dict)
    screen_content_status: str | None = None
    screen_content_selected_path: str | None = None
    screen_content_selected_type: str | None = None
    screen_content_result: dict[str, Any] = field(default_factory=dict)
    screen_content_points: list[dict[str, Any]] = field(default_factory=list)
    screen_content_segments: list[dict[str, Any]] = field(default_factory=list)
    screen_content_point_count: int = 0
    screen_content_segment_count: int = 0
    screen_content_gameplay_segment_count: int = 0
    screen_content_menu_segment_count: int = 0
    screen_content_loading_segment_count: int = 0
    screen_content_scoreboard_segment_count: int = 0
    screen_content_death_screen_segment_count: int = 0
    screen_content_victory_screen_segment_count: int = 0
    screen_content_black_screen_segment_count: int = 0
    screen_content_duration_seconds: float | None = None
    screen_content_frame_sample_rate: float = 2.0
    screen_content_recommendation: str | None = None
    visual_energy_report: dict[str, Any] = field(default_factory=dict)
    visual_energy_status: str | None = None
    visual_energy_result: dict[str, Any] = field(default_factory=dict)
    visual_energy_points: list[dict[str, Any]] = field(default_factory=list)
    visual_energy_segments: list[dict[str, Any]] = field(default_factory=list)
    visual_energy_point_count: int = 0
    visual_energy_segment_count: int = 0
    visual_energy_high_segment_count: int = 0
    visual_energy_low_segment_count: int = 0
    visual_energy_technical_warning_segment_count: int = 0
    visual_energy_duration_seconds: float | None = None
    visual_energy_frame_sample_rate: float = 2.0
    visual_energy_recommendation: str | None = None

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
    # New fields for dashboard
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
            transcript_normalized_segment_count=int(data.get("transcript_normalized_segment_count", 0) or 0),
            transcript_valid_segment_count=int(data.get("transcript_valid_segment_count", 0) or 0),
            transcript_invalid_segment_count=int(data.get("transcript_invalid_segment_count", 0) or 0),
            transcript_word_count=int(data.get("transcript_word_count", 0) or 0),
            transcript_normalized_word_count=int(data.get("transcript_normalized_word_count", 0) or 0),
            transcript_word_timestamp_count=int(data.get("transcript_word_timestamp_count", 0) or 0),
            transcript_has_word_level_timestamps=bool(data.get("transcript_has_word_level_timestamps", False)),
            transcript_segment_normalization_status=data.get("transcript_segment_normalization_status"),
            transcript_segment_normalization_recommendation=data.get("transcript_segment_normalization_recommendation"),
            sentence_boundary_report=dict(data.get("sentence_boundary_report") or {}),
            sentence_boundary_status=data.get("sentence_boundary_status"),
            sentence_boundary_boundaries=list(data.get("sentence_boundary_boundaries") or []),
            sentence_boundary_protection_zones=list(data.get("sentence_boundary_protection_zones") or []),
            sentence_boundary_boundary_count=int(data.get("sentence_boundary_boundary_count", 0) or 0),
            sentence_boundary_protection_zone_count=int(data.get("sentence_boundary_protection_zone_count", 0) or 0),
            sentence_boundary_complete_sentence_count=int(data.get("sentence_boundary_complete_sentence_count", 0) or 0),
            sentence_boundary_open_fragment_count=int(data.get("sentence_boundary_open_fragment_count", 0) or 0),
            sentence_boundary_question_count=int(data.get("sentence_boundary_question_count", 0) or 0),
            sentence_boundary_open_question_count=int(data.get("sentence_boundary_open_question_count", 0) or 0),
            sentence_boundary_safe_boundary_count=int(data.get("sentence_boundary_safe_boundary_count", 0) or 0),
            sentence_boundary_unsafe_boundary_count=int(data.get("sentence_boundary_unsafe_boundary_count", 0) or 0),
            sentence_boundary_recommendation=data.get("sentence_boundary_recommendation"),
            keyword_emotion_report=dict(data.get("keyword_emotion_report") or {}),
            keyword_emotion_status=data.get("keyword_emotion_status"),
            keyword_emotion_matches=list(data.get("keyword_emotion_matches") or []),
            keyword_emotion_segment_scores=list(data.get("keyword_emotion_segment_scores") or []),
            keyword_emotion_match_count=int(data.get("keyword_emotion_match_count", 0) or 0),
            keyword_emotion_segment_score_count=int(data.get("keyword_emotion_segment_score_count", 0) or 0),
            keyword_emotion_hype_match_count=int(data.get("keyword_emotion_hype_match_count", 0) or 0),
            keyword_emotion_frustration_match_count=int(data.get("keyword_emotion_frustration_match_count", 0) or 0),
            keyword_emotion_shock_match_count=int(data.get("keyword_emotion_shock_match_count", 0) or 0),
            keyword_emotion_laugh_match_count=int(data.get("keyword_emotion_laugh_match_count", 0) or 0),
            keyword_emotion_question_match_count=int(data.get("keyword_emotion_question_match_count", 0) or 0),
            keyword_emotion_high_value_segment_count=int(data.get("keyword_emotion_high_value_segment_count", 0) or 0),
            keyword_emotion_recommendation=data.get("keyword_emotion_recommendation"),
            interaction_classification_report=dict(data.get("interaction_classification_report") or {}),
            interaction_classification_status=data.get("interaction_classification_status"),
            interaction_classification_points=list(data.get("interaction_classification_points") or []),
            interaction_classification_segments=list(data.get("interaction_classification_segments") or []),
            interaction_classification_point_count=int(data.get("interaction_classification_point_count", 0) or 0),
            interaction_classification_segment_count=int(data.get("interaction_classification_segment_count", 0) or 0),
            interaction_classification_monologue_count=int(data.get("interaction_classification_monologue_count", 0) or 0),
            interaction_classification_interaction_count=int(data.get("interaction_classification_interaction_count", 0) or 0),
            interaction_classification_question_answer_count=int(data.get("interaction_classification_question_answer_count", 0) or 0),
            interaction_classification_chat_reaction_count=int(data.get("interaction_classification_chat_reaction_count", 0) or 0),
            interaction_classification_callout_count=int(data.get("interaction_classification_callout_count", 0) or 0),
            interaction_classification_commentary_count=int(data.get("interaction_classification_commentary_count", 0) or 0),
            interaction_classification_private_or_meta_count=int(data.get("interaction_classification_private_or_meta_count", 0) or 0),
            interaction_classification_context_needed_count=int(data.get("interaction_classification_context_needed_count", 0) or 0),
            interaction_classification_recommendation=data.get("interaction_classification_recommendation"),
            dead_content_report=dict(data.get("dead_content_report") or {}),
            dead_content_status=data.get("dead_content_status"),
            dead_content_candidates=list(data.get("dead_content_candidates") or []),
            dead_content_segment_scores=list(data.get("dead_content_segment_scores") or []),
            dead_content_candidate_count=int(data.get("dead_content_candidate_count", 0) or 0),
            dead_content_segment_score_count=int(data.get("dead_content_segment_score_count", 0) or 0),
            dead_content_dead_air_candidate_count=int(data.get("dead_content_dead_air_candidate_count", 0) or 0),
            dead_content_low_value_candidate_count=int(data.get("dead_content_low_value_candidate_count", 0) or 0),
            dead_content_filler_pause_candidate_count=int(data.get("dead_content_filler_pause_candidate_count", 0) or 0),
            dead_content_loading_or_menu_candidate_count=int(data.get("dead_content_loading_or_menu_candidate_count", 0) or 0),
            dead_content_private_or_meta_candidate_count=int(data.get("dead_content_private_or_meta_candidate_count", 0) or 0),
            dead_content_protected_candidate_count=int(data.get("dead_content_protected_candidate_count", 0) or 0),
            dead_content_high_confidence_candidate_count=int(data.get("dead_content_high_confidence_candidate_count", 0) or 0),
            dead_content_recommendation=data.get("dead_content_recommendation"),
            content_value_report=dict(data.get("content_value_report") or {}),
            content_value_status=data.get("content_value_status"),
            content_value_segment_scores=list(data.get("content_value_segment_scores") or []),
            content_value_segment_score_count=int(data.get("content_value_segment_score_count", 0) or 0),
            content_value_high_value_count=int(data.get("content_value_high_value_count", 0) or 0),
            content_value_mid_value_count=int(data.get("content_value_mid_value_count", 0) or 0),
            content_value_low_value_count=int(data.get("content_value_low_value_count", 0) or 0),
            content_value_protected_context_count=int(data.get("content_value_protected_context_count", 0) or 0),
            content_value_hook_candidate_count=int(data.get("content_value_hook_candidate_count", 0) or 0),
            content_value_technical_warning_count=int(data.get("content_value_technical_warning_count", 0) or 0),
            content_value_avg_score=float(data.get("content_value_avg_score", 0.0) or 0.0),
            content_value_max_score=float(data.get("content_value_max_score", 0.0) or 0.0),
            content_value_min_score=float(data.get("content_value_min_score", 0.0) or 0.0),
            content_value_recommendation=data.get("content_value_recommendation"),
            profanity_censor_report=dict(data.get("profanity_censor_report") or {}),
            profanity_censor_status=data.get("profanity_censor_status"),
            profanity_censor_matches=list(data.get("profanity_censor_matches") or []),
            profanity_censor_segment_results=list(data.get("profanity_censor_segment_results") or []),
            profanity_censor_match_count=int(data.get("profanity_censor_match_count", 0) or 0),
            profanity_censor_severe_match_count=int(data.get("profanity_censor_severe_match_count", 0) or 0),
            profanity_censor_mild_match_count=int(data.get("profanity_censor_mild_match_count", 0) or 0),
            profanity_censor_required_count=int(data.get("profanity_censor_required_count", 0) or 0),
            profanity_censor_word_level_match_count=int(data.get("profanity_censor_word_level_match_count", 0) or 0),
            profanity_censor_segment_fallback_match_count=int(data.get("profanity_censor_segment_fallback_match_count", 0) or 0),
            profanity_censor_recommendation=data.get("profanity_censor_recommendation"),
            unified_edit_signal_report=dict(data.get("unified_edit_signal_report") or {}),
            unified_edit_signal_status=data.get("unified_edit_signal_status"),
            unified_edit_signals=list(data.get("unified_edit_signals") or []),
            unified_edit_signal_count=int(data.get("unified_edit_signal_count", 0) or 0),
            unified_edit_signal_summary=dict(data.get("unified_edit_signal_summary") or {}),
            unified_edit_signal_recommendation=data.get("unified_edit_signal_recommendation"),
            segment_classification_report=dict(data.get("segment_classification_report") or {}),
            segment_classification_status=data.get("segment_classification_status"),
            segment_classification_segments=list(data.get("segment_classification_segments") or []),
            segment_classification_segment_count=int(data.get("segment_classification_segment_count", 0) or 0),
            segment_classification_highlight_count=int(data.get("segment_classification_highlight_count", 0) or 0),
            segment_classification_hook_candidate_count=int(data.get("segment_classification_hook_candidate_count", 0) or 0),
            segment_classification_protected_context_count=int(data.get("segment_classification_protected_context_count", 0) or 0),
            segment_classification_dead_candidate_count=int(data.get("segment_classification_dead_candidate_count", 0) or 0),
            segment_classification_filler_count=int(data.get("segment_classification_filler_count", 0) or 0),
            segment_classification_transition_count=int(data.get("segment_classification_transition_count", 0) or 0),
            segment_classification_censor_required_count=int(data.get("segment_classification_censor_required_count", 0) or 0),
            segment_classification_technical_warning_count=int(data.get("segment_classification_technical_warning_count", 0) or 0),
            segment_classification_recommendation=data.get("segment_classification_recommendation"),
            murch_scoring_report=dict(data.get("murch_scoring_report") or {}),
            murch_scoring_status=data.get("murch_scoring_status"),
            murch_scoring_segment_scores=list(data.get("murch_scoring_segment_scores") or []),
            murch_scoring_segment_score_count=int(data.get("murch_scoring_segment_score_count", 0) or 0),
            murch_scoring_high_score_count=int(data.get("murch_scoring_high_score_count", 0) or 0),
            murch_scoring_medium_score_count=int(data.get("murch_scoring_medium_score_count", 0) or 0),
            murch_scoring_low_score_count=int(data.get("murch_scoring_low_score_count", 0) or 0),
            murch_scoring_protected_context_count=int(data.get("murch_scoring_protected_context_count", 0) or 0),
            murch_scoring_censor_required_count=int(data.get("murch_scoring_censor_required_count", 0) or 0),
            murch_scoring_technical_warning_count=int(data.get("murch_scoring_technical_warning_count", 0) or 0),
            murch_scoring_avg_score=float(data.get("murch_scoring_avg_score", 0.0) or 0.0),
            murch_scoring_max_score=float(data.get("murch_scoring_max_score", 0.0) or 0.0),
            murch_scoring_min_score=float(data.get("murch_scoring_min_score", 0.0) or 0.0),
            murch_scoring_recommendation=data.get("murch_scoring_recommendation"),
            cut_list_report=dict(data.get("cut_list_report") or {}),
            cut_list_status=data.get("cut_list_status"),
            cut_list_items=list(data.get("cut_list_items") or []),
            cut_list_item_count=int(data.get("cut_list_item_count", 0) or 0),
            cut_list_keep_count=int(data.get("cut_list_keep_count", 0) or 0),
            cut_list_review_keep_count=int(data.get("cut_list_review_keep_count", 0) or 0),
            cut_list_review_trim_count=int(data.get("cut_list_review_trim_count", 0) or 0),
            cut_list_review_remove_count=int(data.get("cut_list_review_remove_count", 0) or 0),
            cut_list_protect_count=int(data.get("cut_list_protect_count", 0) or 0),
            cut_list_censor_keep_count=int(data.get("cut_list_censor_keep_count", 0) or 0),
            cut_list_technical_review_count=int(data.get("cut_list_technical_review_count", 0) or 0),
            cut_list_unknown_review_count=int(data.get("cut_list_unknown_review_count", 0) or 0),
            cut_list_recommendation=data.get("cut_list_recommendation"),
            clip_duration_report=dict(data.get("clip_duration_report") or {}),
            clip_duration_status=data.get("clip_duration_status"),
            clip_duration_recommendations=list(data.get("clip_duration_recommendations") or []),
            clip_duration_recommendation_count=int(data.get("clip_duration_recommendation_count", 0) or 0),
            clip_duration_ok_count=int(data.get("clip_duration_ok_count", 0) or 0),
            clip_duration_too_short_count=int(data.get("clip_duration_too_short_count", 0) or 0),
            clip_duration_too_long_count=int(data.get("clip_duration_too_long_count", 0) or 0),
            clip_duration_trim_review_count=int(data.get("clip_duration_trim_review_count", 0) or 0),
            clip_duration_extend_review_count=int(data.get("clip_duration_extend_review_count", 0) or 0),
            clip_duration_protect_duration_count=int(data.get("clip_duration_protect_duration_count", 0) or 0),
            clip_duration_censor_keep_count=int(data.get("clip_duration_censor_keep_count", 0) or 0),
            clip_duration_technical_review_count=int(data.get("clip_duration_technical_review_count", 0) or 0),
            clip_duration_invalid_timing_count=int(data.get("clip_duration_invalid_timing_count", 0) or 0),
            clip_duration_recommendation=data.get("clip_duration_recommendation"),            
            transition_decision_report=dict(data.get("transition_decision_report") or {}),
            transition_decision_status=data.get("transition_decision_status"),
            transition_decision_decisions=list(data.get("transition_decision_decisions") or []),
            transition_decision_count=int(data.get("transition_decision_count", 0) or 0),
            transition_decision_hard_cut_review_count=int(data.get("transition_decision_hard_cut_review_count", 0) or 0),
            transition_decision_j_cut_review_count=int(data.get("transition_decision_j_cut_review_count", 0) or 0),
            transition_decision_l_cut_review_count=int(data.get("transition_decision_l_cut_review_count", 0) or 0),
            transition_decision_quick_fade_review_count=int(data.get("transition_decision_quick_fade_review_count", 0) or 0),
            transition_decision_no_cut_protect_count=int(data.get("transition_decision_no_cut_protect_count", 0) or 0),
            transition_decision_censor_safe_keep_count=int(data.get("transition_decision_censor_safe_keep_count", 0) or 0),
            transition_decision_technical_review_count=int(data.get("transition_decision_technical_review_count", 0) or 0),
            transition_decision_unknown_review_count=int(data.get("transition_decision_unknown_review_count", 0) or 0),
            transition_decision_recommendation=data.get("transition_decision_recommendation"),
            continuity_check_report=dict(data.get("continuity_check_report") or {}),
            continuity_check_status=data.get("continuity_check_status"),
            continuity_check_issues=list(data.get("continuity_check_issues") or []),
            continuity_check_issue_count=int(data.get("continuity_check_issue_count", 0) or 0),
            continuity_check_blocking_issue_count=int(data.get("continuity_check_blocking_issue_count", 0) or 0),
            continuity_check_sentence_break_risk_count=int(data.get("continuity_check_sentence_break_risk_count", 0) or 0),
            continuity_check_context_jump_risk_count=int(data.get("continuity_check_context_jump_risk_count", 0) or 0),
            continuity_check_censor_context_risk_count=int(data.get("continuity_check_censor_context_risk_count", 0) or 0),
            continuity_check_timing_issue_count=int(data.get("continuity_check_timing_issue_count", 0) or 0),
            continuity_check_transition_conflict_count=int(data.get("continuity_check_transition_conflict_count", 0) or 0),
            continuity_check_technical_issue_count=int(data.get("continuity_check_technical_issue_count", 0) or 0),
            continuity_check_protected_context_count=int(data.get("continuity_check_protected_context_count", 0) or 0),
            continuity_check_recommendation=data.get("continuity_check_recommendation"),
            final_cut_list_report=dict(data.get("final_cut_list_report") or {}),
            final_cut_list_status=data.get("final_cut_list_status"),
            final_cut_list_items=list(data.get("final_cut_list_items") or []),
            final_cut_list_item_count=int(data.get("final_cut_list_item_count", 0) or 0),
            final_cut_list_keep_review_count=int(data.get("final_cut_list_keep_review_count", 0) or 0),
            final_cut_list_keep_high_value_count=int(data.get("final_cut_list_keep_high_value_count", 0) or 0),
            final_cut_list_trim_review_count=int(data.get("final_cut_list_trim_review_count", 0) or 0),
            final_cut_list_remove_review_count=int(data.get("final_cut_list_remove_review_count", 0) or 0),
            final_cut_list_protect_count=int(data.get("final_cut_list_protect_count", 0) or 0),
            final_cut_list_censor_keep_count=int(data.get("final_cut_list_censor_keep_count", 0) or 0),
            final_cut_list_technical_review_count=int(data.get("final_cut_list_technical_review_count", 0) or 0),
            final_cut_list_blocked_by_continuity_count=int(data.get("final_cut_list_blocked_by_continuity_count", 0) or 0),
            final_cut_list_unknown_review_count=int(data.get("final_cut_list_unknown_review_count", 0) or 0),
            final_cut_list_review_required_count=int(data.get("final_cut_list_review_required_count", 0) or 0),
            final_cut_list_blocking_issue_count=int(data.get("final_cut_list_blocking_issue_count", 0) or 0),
            final_cut_list_recommendation=data.get("final_cut_list_recommendation"),
            review_timeline_plan_report=dict(
                data.get("review_timeline_plan_report") or {}
            ),
            review_timeline_plan=dict(data.get("review_timeline_plan") or {}),
            review_timeline_plan_status=data.get("review_timeline_plan_status"),
            review_timeline_plan_id=data.get("review_timeline_plan_id"),
            review_timeline_plan_items=list(
                data.get("review_timeline_plan_items") or []
            ),
            review_timeline_plan_item_count=int(
                data.get("review_timeline_plan_item_count", 0) or 0
            ),
            review_timeline_plan_total_duration_seconds=float(
                data.get("review_timeline_plan_total_duration_seconds", 0.0)
                or 0.0
            ),
            review_timeline_plan_review_required_count=int(
                data.get("review_timeline_plan_review_required_count", 0) or 0
            ),
            review_timeline_plan_protected_count=int(
                data.get("review_timeline_plan_protected_count", 0) or 0
            ),
            review_timeline_plan_censor_required_count=int(
                data.get("review_timeline_plan_censor_required_count", 0) or 0
            ),
            review_timeline_plan_continuity_blocked_count=int(
                data.get("review_timeline_plan_continuity_blocked_count", 0) or 0
            ),
            review_timeline_plan_recommendation=data.get(
                "review_timeline_plan_recommendation"
                    ),
            timeline_approval_gate_report=dict(
                data.get("timeline_approval_gate_report") or {}
            ),
            timeline_approval_gate=dict(data.get("timeline_approval_gate") or {}),
            timeline_approval_gate_status=data.get("timeline_approval_gate_status"),
            timeline_approval_gate_id=data.get("timeline_approval_gate_id"),
            timeline_approval_status=data.get("timeline_approval_status"),
            timeline_approval_requested_status=data.get(
                "timeline_approval_requested_status"
            ),
            timeline_approved_by=data.get("timeline_approved_by"),
            timeline_rejected_by=data.get("timeline_rejected_by"),
            timeline_manual_change_reason=data.get("timeline_manual_change_reason"),
            timeline_can_proceed_to_execution=bool(
                data.get("timeline_can_proceed_to_execution", False)
            ),
            timeline_can_render=bool(data.get("timeline_can_render", False)),
            timeline_requires_human_approval=bool(
                data.get("timeline_requires_human_approval", True)
            ),
            timeline_approval_blocking_reasons=list(
                data.get("timeline_approval_blocking_reasons") or []
            ),
            timeline_approval_warnings=list(data.get("timeline_approval_warnings") or []),
            timeline_safety_validator_report=dict(
                data.get("timeline_safety_validator_report") or {}
            ),
            timeline_safety_validator=dict(
                data.get("timeline_safety_validator") or {}
            ),
            timeline_safety_validation_id=data.get("timeline_safety_validation_id"),
            timeline_safety_validation_status=data.get(
                "timeline_safety_validation_status"
            ),
            timeline_is_safe_for_future_execution=bool(
                data.get("timeline_is_safe_for_future_execution", False)
            ),
            timeline_is_safe_for_render=bool(
                data.get("timeline_is_safe_for_render", False)
            ),
            timeline_safety_requires_manual_review=bool(
                data.get("timeline_safety_requires_manual_review", True)
            ),
            timeline_safety_blocking_errors=list(
                data.get("timeline_safety_blocking_errors") or []
            ),
            timeline_safety_warnings=list(
                data.get("timeline_safety_warnings") or []
            ),
            timeline_safety_item_results=list(
                data.get("timeline_safety_item_results") or []
            ),
            timeline_safety_invalid_timing_count=int(
                data.get("timeline_safety_invalid_timing_count", 0) or 0
            ),
            timeline_safety_overlap_count=int(
                data.get("timeline_safety_overlap_count", 0) or 0
            ),
            timeline_safety_gap_count=int(
                data.get("timeline_safety_gap_count", 0) or 0
            ),
            timeline_safety_protected_violation_count=int(
                data.get("timeline_safety_protected_violation_count", 0) or 0
            ),
            timeline_safety_censor_violation_count=int(
                data.get("timeline_safety_censor_violation_count", 0) or 0
            ),
            timeline_safety_continuity_violation_count=int(
                data.get("timeline_safety_continuity_violation_count", 0) or 0
            ),
            timeline_safety_approval_violation_count=int(
                data.get("timeline_safety_approval_violation_count", 0) or 0
            ),
            review_timeline_dashboard_package_report=dict(data.get("review_timeline_dashboard_package_report", {}) or {}),
            review_timeline_dashboard_package=dict(data.get("review_timeline_dashboard_package", {}) or {}),
            review_timeline_dashboard_package_id=data.get("review_timeline_dashboard_package_id"),
            review_timeline_dashboard_package_status=data.get("review_timeline_dashboard_package_status"),
            review_timeline_dashboard_review_status=data.get("review_timeline_dashboard_review_status"),
            review_timeline_dashboard_approval_status=data.get("review_timeline_dashboard_approval_status"),
            review_timeline_dashboard_safety_status=data.get("review_timeline_dashboard_safety_status"),
            review_timeline_dashboard_can_proceed_to_execution=bool(data.get("review_timeline_dashboard_can_proceed_to_execution", False)),
            review_timeline_dashboard_can_render=False,
            review_timeline_dashboard_requires_manual_review=bool(data.get("review_timeline_dashboard_requires_manual_review", True)),
            review_timeline_dashboard_is_safe_for_future_execution=bool(data.get("review_timeline_dashboard_is_safe_for_future_execution", False)),
            review_timeline_dashboard_is_safe_for_render=False,
            review_timeline_dashboard_summary=dict(data.get("review_timeline_dashboard_summary", {}) or {}),
            review_timeline_dashboard_counters=dict(data.get("review_timeline_dashboard_counters", {}) or {}),
            review_timeline_dashboard_item_cards=list(data.get("review_timeline_dashboard_item_cards", []) or []),
            review_timeline_dashboard_approval_panel=dict(data.get("review_timeline_dashboard_approval_panel", {}) or {}),
            review_timeline_dashboard_safety_panel=dict(data.get("review_timeline_dashboard_safety_panel", {}) or {}),
            review_timeline_dashboard_warnings=list(data.get("review_timeline_dashboard_warnings", []) or []),
            review_timeline_dashboard_blocking_errors=list(data.get("review_timeline_dashboard_blocking_errors", []) or []),
            review_timeline_dashboard_actions=list(data.get("review_timeline_dashboard_actions", []) or []),
            hook_identification_report=dict(data.get("hook_identification_report") or {}),
            hook_identification=dict(data.get("hook_identification") or {}),
            hook_identification_status=data.get("hook_identification_status"),
            hook_candidates=list(data.get("hook_candidates") or []),
            hook_selected_candidate=(
                dict(data.get("hook_selected_candidate") or {})
                if data.get("hook_selected_candidate") is not None
                else None
            ),
            hook_best_score=float(data.get("hook_best_score", 0.0) or 0.0),
            hook_review_required=bool(data.get("hook_review_required", True)),
            hook_can_apply=False,
            hook_can_reorder_timeline=False,
            hook_can_render=False,
            hook_blocking_reasons=list(data.get("hook_blocking_reasons") or []),
            hook_warnings=list(data.get("hook_warnings") or []),
            hook_recommendation=data.get("hook_recommendation"),
            emotional_arc_report=dict(data.get("emotional_arc_report") or {}),
            emotional_arc=dict(data.get("emotional_arc") or {}),
            emotional_arc_status=data.get("emotional_arc_status"),
            emotional_arc_points=list(data.get("emotional_arc_points") or []),
            emotional_arc_suggestions=list(
                data.get("emotional_arc_suggestions") or []
            ),
            emotional_arc_average_deviation=float(
                data.get("emotional_arc_average_deviation", 0.0) or 0.0
            ),
            emotional_arc_max_deviation=float(
                data.get("emotional_arc_max_deviation", 0.0) or 0.0
            ),
            emotional_arc_flatness_score=float(
                data.get("emotional_arc_flatness_score", 0.0) or 0.0
            ),
            emotional_arc_hook_strength_score=float(
                data.get("emotional_arc_hook_strength_score", 0.0) or 0.0
            ),
            emotional_arc_climax_strength_score=float(
                data.get("emotional_arc_climax_strength_score", 0.0) or 0.0
            ),
            emotional_arc_breathing_room_score=float(
                data.get("emotional_arc_breathing_room_score", 0.0) or 0.0
            ),
            emotional_arc_review_required=bool(
                data.get("emotional_arc_review_required", True)
            ),
            emotional_arc_can_apply=False,
            emotional_arc_can_reorder_timeline=False,
            emotional_arc_can_trim=False,
            emotional_arc_can_extend=False,
            emotional_arc_can_render=False,
            emotional_arc_blocking_reasons=list(
                data.get("emotional_arc_blocking_reasons") or []
            ),
            emotional_arc_warnings=list(data.get("emotional_arc_warnings") or []),
            emotional_arc_recommendation=data.get("emotional_arc_recommendation"),
            dynamic_pacing_report=dict(data.get("dynamic_pacing_report") or {}),
            dynamic_pacing=dict(data.get("dynamic_pacing") or {}),
            dynamic_pacing_status=data.get("dynamic_pacing_status"),
            dynamic_pacing_segments=list(data.get("dynamic_pacing_segments") or []),
            dynamic_pacing_suggestions=list(
                data.get("dynamic_pacing_suggestions") or []
            ),
            dynamic_pacing_average_cut_rate=float(
                data.get("dynamic_pacing_average_cut_rate", 0.0) or 0.0
            ),
            dynamic_pacing_target_cut_rate_range=dict(
                data.get("dynamic_pacing_target_cut_rate_range") or {}
            ),
            dynamic_pacing_match_score=float(
                data.get("dynamic_pacing_match_score", 0.0) or 0.0
            ),
            dynamic_pacing_monotony_score=float(
                data.get("dynamic_pacing_monotony_score", 0.0) or 0.0
            ),
            dynamic_pacing_breathing_room_score=float(
                data.get("dynamic_pacing_breathing_room_score", 0.0) or 0.0
            ),
            dynamic_pacing_fast_run_count=int(
                data.get("dynamic_pacing_fast_run_count", 0) or 0
            ),
            dynamic_pacing_slow_run_count=int(
                data.get("dynamic_pacing_slow_run_count", 0) or 0
            ),
            dynamic_pacing_review_required=bool(
                data.get("dynamic_pacing_review_required", True)
            ),
            dynamic_pacing_can_apply=False,
            dynamic_pacing_can_split_clips=False,
            dynamic_pacing_can_merge_clips=False,
            dynamic_pacing_can_trim=False,
            dynamic_pacing_can_extend=False,
            dynamic_pacing_can_reorder_timeline=False,
            dynamic_pacing_can_render=False,
            dynamic_pacing_blocking_reasons=list(
                data.get("dynamic_pacing_blocking_reasons") or []
            ),
            dynamic_pacing_warnings=list(data.get("dynamic_pacing_warnings") or []),
            dynamic_pacing_recommendation=data.get("dynamic_pacing_recommendation"),
            pattern_interrupt_report=dict(data.get("pattern_interrupt_report") or {}),
            pattern_interrupt=dict(data.get("pattern_interrupt") or {}),
            pattern_interrupt_status=data.get("pattern_interrupt_status"),
            pattern_interrupt_windows=list(
                data.get("pattern_interrupt_windows") or []
            ),
            pattern_interrupt_suggestions=list(
                data.get("pattern_interrupt_suggestions") or []
            ),
            pattern_interrupt_total_windows=int(
                data.get("pattern_interrupt_total_windows", 0) or 0
            ),
            pattern_interrupt_needed_count=int(
                data.get("pattern_interrupt_needed_count", 0) or 0
            ),
            pattern_interrupt_monotony_score=float(
                data.get("pattern_interrupt_monotony_score", 0.0) or 0.0
            ),
            pattern_interrupt_average_window_duration_seconds=float(
                data.get(
                    "pattern_interrupt_average_window_duration_seconds",
                    0.0,
                )
                or 0.0
            ),
            pattern_interrupt_recommended_count=int(
                data.get("pattern_interrupt_recommended_count", 0) or 0
            ),
            pattern_interrupt_review_required=bool(
                data.get("pattern_interrupt_review_required", True)
            ),
            pattern_interrupt_can_apply=False,
            pattern_interrupt_can_insert_zoom=False,
            pattern_interrupt_can_insert_text_overlay=False,
            pattern_interrupt_can_insert_sfx=False,
            pattern_interrupt_can_reorder_timeline=False,
            pattern_interrupt_can_trim=False,
            pattern_interrupt_can_extend=False,
            pattern_interrupt_can_render=False,
            pattern_interrupt_blocking_reasons=list(
                data.get("pattern_interrupt_blocking_reasons") or []
            ),
            pattern_interrupt_warnings=list(
                data.get("pattern_interrupt_warnings") or []
            ),
            pattern_interrupt_recommendation=data.get(
                "pattern_interrupt_recommendation"
            ),
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
            scene_change_report=dict(data.get("scene_change_report") or {}),
            scene_change_status=data.get("scene_change_status"),
            scene_change_selected_path=data.get("scene_change_selected_path"),
            scene_change_selected_type=data.get("scene_change_selected_type"),
            scene_change_result=dict(data.get("scene_change_result") or {}),
            scene_changes=list(data.get("scene_changes") or []),
            scene_change_count=int(data.get("scene_change_count", 0) or 0),
            scene_change_hard_count=int(data.get("scene_change_hard_count", 0) or 0),
            scene_change_soft_count=int(data.get("scene_change_soft_count", 0) or 0),
            scene_change_false_positive_candidate_count=int(
                data.get("scene_change_false_positive_candidate_count", 0) or 0
            ),
            scene_change_threshold=float(data.get("scene_change_threshold", 0.30) or 0.30),
            scene_change_duration_seconds=(
                float(data["scene_change_duration_seconds"])
                if data.get("scene_change_duration_seconds") is not None
                else None
            ),
            scene_change_recommendation=data.get("scene_change_recommendation"),
            motion_analysis_report=dict(data.get("motion_analysis_report") or {}),
            motion_analysis_status=data.get("motion_analysis_status"),
            motion_analysis_selected_path=data.get("motion_analysis_selected_path"),
            motion_analysis_selected_type=data.get("motion_analysis_selected_type"),
            motion_analysis_result=dict(data.get("motion_analysis_result") or {}),
            motion_analysis_points=list(data.get("motion_analysis_points") or []),
            motion_analysis_segments=list(data.get("motion_analysis_segments") or []),
            motion_analysis_point_count=int(
                data.get("motion_analysis_point_count", 0) or 0
            ),
            motion_analysis_segment_count=int(
                data.get("motion_analysis_segment_count", 0) or 0
            ),
            motion_analysis_low_motion_segment_count=int(
                data.get("motion_analysis_low_motion_segment_count", 0) or 0
            ),
            motion_analysis_high_motion_segment_count=int(
                data.get("motion_analysis_high_motion_segment_count", 0) or 0
            ),
            motion_analysis_dead_visual_candidate_count=int(
                data.get("motion_analysis_dead_visual_candidate_count", 0) or 0
            ),
            motion_analysis_duration_seconds=(
                float(data["motion_analysis_duration_seconds"])
                if data.get("motion_analysis_duration_seconds") is not None
                else None
            ),
            motion_analysis_frame_sample_rate=float(
                data.get("motion_analysis_frame_sample_rate", 2.0) or 2.0
            ),
            motion_analysis_recommendation=data.get("motion_analysis_recommendation"),
            face_reaction_report=dict(data.get("face_reaction_report") or {}),
            face_reaction_status=data.get("face_reaction_status"),
            face_reaction_selected_path=data.get("face_reaction_selected_path"),
            face_reaction_selected_type=data.get("face_reaction_selected_type"),
            face_reaction_result=dict(data.get("face_reaction_result") or {}),
            face_reaction_points=list(data.get("face_reaction_points") or []),
            face_reaction_segments=list(data.get("face_reaction_segments") or []),
            face_reaction_point_count=int(
                data.get("face_reaction_point_count", 0) or 0
            ),
            face_reaction_segment_count=int(
                data.get("face_reaction_segment_count", 0) or 0
            ),
            face_reaction_detected_point_count=int(
                data.get("face_reaction_detected_point_count", 0) or 0
            ),
            face_reaction_candidate_count=int(
                data.get("face_reaction_candidate_count", 0) or 0
            ),
            face_reaction_high_segment_count=int(
                data.get("face_reaction_high_segment_count", 0) or 0
            ),
            face_reaction_duration_seconds=(
                float(data["face_reaction_duration_seconds"])
                if data.get("face_reaction_duration_seconds") is not None
                else None
            ),
            face_reaction_frame_sample_rate=float(
                data.get("face_reaction_frame_sample_rate", 2.0) or 2.0
            ),
            face_reaction_recommendation=data.get("face_reaction_recommendation"),
            stutter_detection_report=dict(data.get("stutter_detection_report") or {}),
            stutter_detection_status=data.get("stutter_detection_status"),
            stutter_detection_selected_path=data.get("stutter_detection_selected_path"),
            stutter_detection_selected_type=data.get("stutter_detection_selected_type"),
            stutter_detection_result=dict(data.get("stutter_detection_result") or {}),
            stutter_detection_points=list(data.get("stutter_detection_points") or []),
            stutter_detection_segments=list(
                data.get("stutter_detection_segments") or []
            ),
            stutter_detection_point_count=int(
                data.get("stutter_detection_point_count", 0) or 0
            ),
            stutter_detection_segment_count=int(
                data.get("stutter_detection_segment_count", 0) or 0
            ),
            stutter_detection_duplicate_candidate_count=int(
                data.get("stutter_detection_duplicate_candidate_count", 0) or 0
            ),
            stutter_detection_stutter_segment_count=int(
                data.get("stutter_detection_stutter_segment_count", 0) or 0
            ),
            stutter_detection_freeze_segment_count=int(
                data.get("stutter_detection_freeze_segment_count", 0) or 0
            ),
            stutter_detection_duration_seconds=(
                float(data["stutter_detection_duration_seconds"])
                if data.get("stutter_detection_duration_seconds") is not None
                else None
            ),
            stutter_detection_frame_sample_rate=float(
                data.get("stutter_detection_frame_sample_rate", 10.0) or 10.0
            ),
            stutter_detection_recommendation=data.get(
                "stutter_detection_recommendation"
            ),
            screen_content_report=dict(data.get("screen_content_report") or {}),
            screen_content_status=data.get("screen_content_status"),
            screen_content_selected_path=data.get("screen_content_selected_path"),
            screen_content_selected_type=data.get("screen_content_selected_type"),
            screen_content_result=dict(data.get("screen_content_result") or {}),
            screen_content_points=list(data.get("screen_content_points") or []),
            screen_content_segments=list(data.get("screen_content_segments") or []),
            screen_content_point_count=int(
                data.get("screen_content_point_count", 0) or 0
            ),
            screen_content_segment_count=int(
                data.get("screen_content_segment_count", 0) or 0
            ),
            screen_content_gameplay_segment_count=int(
                data.get("screen_content_gameplay_segment_count", 0) or 0
            ),
            screen_content_menu_segment_count=int(
                data.get("screen_content_menu_segment_count", 0) or 0
            ),
            screen_content_loading_segment_count=int(
                data.get("screen_content_loading_segment_count", 0) or 0
            ),
            screen_content_scoreboard_segment_count=int(
                data.get("screen_content_scoreboard_segment_count", 0) or 0
            ),
            screen_content_death_screen_segment_count=int(
                data.get("screen_content_death_screen_segment_count", 0) or 0
            ),
            screen_content_victory_screen_segment_count=int(
                data.get("screen_content_victory_screen_segment_count", 0) or 0
            ),
            screen_content_black_screen_segment_count=int(
                data.get("screen_content_black_screen_segment_count", 0) or 0
            ),
            screen_content_duration_seconds=(
                float(data["screen_content_duration_seconds"])
                if data.get("screen_content_duration_seconds") is not None
                else None
            ),
            screen_content_frame_sample_rate=float(
                data.get("screen_content_frame_sample_rate", 2.0) or 2.0
            ),
            screen_content_recommendation=data.get("screen_content_recommendation"),
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
            # New rerender fields
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
