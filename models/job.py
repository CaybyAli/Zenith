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

    publish_target_channel: ChannelType | None = None

    raw_video_path: str | None = None
    shorts: list[dict[str, Any]] = field(default_factory=list)
    topic: str | None = None
    title: str | None = None
    pipeline_type: PipelineType | None = None
    profile_id: str | None = None
    quality_mode: str | None = None
    power_profile: str = "balanced"
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

    reaction_shot_placement_report: dict[str, Any] = field(default_factory=dict)
    reaction_shot_placement: dict[str, Any] = field(default_factory=dict)
    reaction_shot_placement_status: str | None = None
    reaction_shot_candidates: list[dict[str, Any]] = field(default_factory=list)
    reaction_shot_placements: list[dict[str, Any]] = field(default_factory=list)
    reaction_shot_total_candidates: int = 0
    reaction_shot_total_placements: int = 0
    reaction_shot_best_placement_score: float = 0.0
    reaction_shot_missing_placeholder_count: int = 0
    reaction_shot_review_required: bool = True
    reaction_shot_can_apply: bool = False
    reaction_shot_can_move_clip: bool = False
    reaction_shot_can_insert_clip: bool = False
    reaction_shot_can_trim: bool = False
    reaction_shot_can_extend: bool = False
    reaction_shot_can_reorder_timeline: bool = False
    reaction_shot_can_render: bool = False
    reaction_shot_blocking_reasons: list[str] = field(default_factory=list)
    reaction_shot_warnings: list[str] = field(default_factory=list)
    reaction_shot_recommendation: str | None = None

    but_therefore_story_report: dict[str, Any] = field(default_factory=dict)
    but_therefore_story: dict[str, Any] = field(default_factory=dict)
    but_therefore_story_status: str | None = None
    story_moments: list[dict[str, Any]] = field(default_factory=list)
    story_transitions: list[dict[str, Any]] = field(default_factory=list)
    story_suggestions: list[dict[str, Any]] = field(default_factory=list)
    story_total_moments: int = 0
    story_but_count: int = 0
    story_therefore_count: int = 0
    story_and_count: int = 0
    story_reaction_count: int = 0
    story_payoff_count: int = 0
    story_strong_count: int = 0
    story_but_therefore_ratio: float = 0.0
    story_flow_score: float = 0.0
    story_and_streak_max: int = 0
    story_orphan_reaction_count: int = 0
    story_missing_payoff_count: int = 0
    story_review_required: bool = True
    story_can_apply_changes: bool = False
    story_can_remove_and_moments: bool = False
    story_can_reorder_timeline: bool = False
    story_can_trim: bool = False
    story_can_extend: bool = False
    story_can_render: bool = False
    story_blocking_reasons: list[str] = field(default_factory=list)
    story_warnings: list[str] = field(default_factory=list)
    story_recommendation: str | None = None

    final_quality_validation_report: dict[str, Any] = field(default_factory=dict)
    final_quality_validator: dict[str, Any] = field(default_factory=dict)
    final_quality_validation_status: str | None = None
    final_quality_checks: list[dict[str, Any]] = field(default_factory=list)
    final_quality_suggestions: list[dict[str, Any]] = field(default_factory=list)
    final_quality_audio_score: float = 0.0
    final_quality_video_score: float = 0.0
    final_quality_story_score: float = 0.0
    final_quality_pacing_score: float = 0.0
    final_quality_safety_score: float = 1.0
    final_quality_overall_score: float = 0.0
    final_quality_passed_count: int = 0
    final_quality_warning_count: int = 0
    final_quality_blocking_count: int = 0
    final_quality_review_required: bool = True
    final_quality_can_apply_fixes: bool = False
    final_quality_can_render: bool = False
    final_quality_can_execute_timeline: bool = False
    final_quality_can_reorder_timeline: bool = False
    final_quality_can_trim: bool = False
    final_quality_can_extend: bool = False
    final_quality_can_insert_effects: bool = False
    final_quality_blocking_reasons: list[str] = field(default_factory=list)
    final_quality_warnings: list[str] = field(default_factory=list)
    final_quality_recommendation: str | None = None

    silence_detection_report: dict[str, Any] = field(default_factory=dict)
    silence_detection_result: dict[str, Any] = field(default_factory=dict)
    silence_detection_status: str | None = None
    silence_detection_source_path: str | None = None
    silence_detection_source_type: str | None = None
    silence_detection_threshold_db: float | None = None
    silence_detection_min_duration_seconds: float | None = None
    silence_segment_count: int = 0
    silence_total_seconds: float = 0.0

    render_readiness_guard_report: dict[str, Any] = field(default_factory=dict)
    render_readiness_guard: dict[str, Any] = field(default_factory=dict)
    render_readiness_status: str | None = None
    render_readiness_checks: list[dict[str, Any]] = field(default_factory=list)
    render_readiness_total_checks: int = 0
    render_readiness_passed_count: int = 0
    render_readiness_warning_count: int = 0
    render_readiness_blocking_count: int = 0
    render_readiness_review_required: bool = True
    render_readiness_ready_for_next_render_stage: bool = False
    render_readiness_can_start_render_pipeline: bool = False
    render_readiness_can_render: bool = False
    render_readiness_can_run_ffmpeg: bool = False
    render_readiness_can_execute_media_operations: bool = False
    render_readiness_can_apply_timeline: bool = False
    render_readiness_can_modify_media: bool = False
    render_readiness_blocking_reasons: list[str] = field(default_factory=list)
    render_readiness_warnings: list[str] = field(default_factory=list)
    render_readiness_recommendation: str | None = None

    render_plan_report: dict[str, Any] = field(default_factory=dict)
    render_plan: dict[str, Any] = field(default_factory=dict)
    render_plan_status: str | None = None
    render_plan_sources: list[dict[str, Any]] = field(default_factory=list)
    render_plan_segments: list[dict[str, Any]] = field(default_factory=list)
    render_plan_output_targets: list[dict[str, Any]] = field(default_factory=list)
    render_plan_operation_intents: list[dict[str, Any]] = field(default_factory=list)
    render_plan_total_segments: int = 0
    render_plan_total_duration_seconds: float = 0.0
    render_plan_estimated_output_duration_seconds: float = 0.0
    render_plan_dry_run_only: bool = True
    render_plan_ready_for_renderer_contract: bool = False
    render_plan_can_execute_plan: bool = False
    render_plan_can_render: bool = False
    render_plan_can_run_ffmpeg: bool = False
    render_plan_can_write_media: bool = False
    render_plan_can_apply_timeline: bool = False
    render_plan_blocking_reasons: list[str] = field(default_factory=list)
    render_plan_warnings: list[str] = field(default_factory=list)
    render_plan_recommendation: str | None = None

    render_command_blueprint_report: dict[str, Any] = field(default_factory=dict)
    render_command_blueprint: dict[str, Any] = field(default_factory=dict)
    render_blueprint_status: str | None = None
    render_blueprint_steps: list[dict[str, Any]] = field(default_factory=list)
    render_blueprint_total_steps: int = 0
    render_blueprint_trim_step_count: int = 0
    render_blueprint_concat_step_count: int = 0
    render_blueprint_transition_step_count: int = 0
    render_blueprint_audio_mix_step_count: int = 0
    render_blueprint_censor_sfx_step_count: int = 0
    render_blueprint_subtitle_step_count: int = 0
    render_blueprint_encode_step_count: int = 0
    render_blueprint_dry_run_only: bool = True
    render_blueprint_non_executable: bool = True
    render_blueprint_ready_for_renderer_implementation: bool = False
    render_blueprint_can_execute_contract: bool = False
    render_blueprint_can_render: bool = False
    render_blueprint_can_run_ffmpeg: bool = False
    render_blueprint_can_spawn_process: bool = False
    render_blueprint_can_write_media: bool = False
    render_blueprint_blocking_reasons: list[str] = field(default_factory=list)
    render_blueprint_warnings: list[str] = field(default_factory=list)
    render_blueprint_recommendation: str | None = None

    render_asset_manifest_report: dict[str, Any] = field(default_factory=dict)
    render_asset_manifest: dict[str, Any] = field(default_factory=dict)
    render_asset_manifest_status: str | None = None
    render_asset_references: list[dict[str, Any]] = field(default_factory=list)
    render_output_path_plans: list[dict[str, Any]] = field(default_factory=list)
    render_asset_total_assets: int = 0
    render_asset_required_count: int = 0
    render_asset_missing_required_hint_count: int = 0
    render_asset_unsafe_path_count: int = 0
    render_asset_output_plan_count: int = 0
    render_asset_dry_run_only: bool = True
    render_asset_manifest_only: bool = True
    render_asset_paths_are_hints_only: bool = True
    render_asset_can_create_directories: bool = False
    render_asset_can_write_files: bool = False
    render_asset_can_open_media: bool = False
    render_asset_can_render: bool = False
    render_asset_can_run_ffmpeg: bool = False
    render_asset_blocking_reasons: list[str] = field(default_factory=list)
    render_asset_warnings: list[str] = field(default_factory=list)
    render_asset_recommendation: str | None = None

    render_execution_permission_report: dict[str, Any] = field(default_factory=dict)
    render_execution_permission_gate: dict[str, Any] = field(default_factory=dict)
    render_execution_permission_status: str | None = None
    render_execution_permission_checks: list[dict[str, Any]] = field(default_factory=list)
    render_execution_permission_total_checks: int = 0
    render_execution_permission_passed_count: int = 0
    render_execution_permission_warning_count: int = 0
    render_execution_permission_blocking_count: int = 0
    render_execution_permission_review_required: bool = True
    render_execution_ready_for_real_render_stage: bool = False
    render_execution_can_prepare_real_render_execution: bool = False
    render_execution_can_render: bool = False
    render_execution_can_run_ffmpeg: bool = False
    render_execution_can_spawn_process: bool = False
    render_execution_can_write_media: bool = False
    render_execution_can_apply_timeline: bool = False
    render_execution_human_approved: bool = False
    render_execution_requested_status: str | None = None
    render_execution_approved_by: str | None = None
    render_execution_approved_at: str | None = None
    render_execution_approval_reason: str | None = None
    render_execution_rejected_by: str | None = None
    render_execution_rejection_reason: str | None = None
    render_execution_blocking_reasons: list[str] = field(default_factory=list)
    render_execution_warnings: list[str] = field(default_factory=list)
    render_execution_recommendation: str | None = None

    render_execution_requested_mode: str = "dry_run"
    render_execution_allow_real_render: bool = False
    render_execution_allow_ffmpeg: bool = False
    render_execution_allow_process_spawn: bool = False
    render_execution_allow_media_write: bool = False

    controlled_render_executor_report: dict[str, Any] = field(default_factory=dict)
    controlled_render_executor: dict[str, Any] = field(default_factory=dict)
    controlled_render_executor_status: str | None = None
    controlled_render_execution_request: dict[str, Any] = field(default_factory=dict)
    controlled_render_execution_steps: list[dict[str, Any]] = field(default_factory=list)
    controlled_render_total_steps: int = 0
    controlled_render_planned_step_count: int = 0
    controlled_render_executed_step_count: int = 0
    controlled_render_skipped_step_count: int = 0
    controlled_render_dry_run_only: bool = True
    controlled_render_real_render_requested: bool = False
    controlled_render_real_render_allowed: bool = False
    controlled_render_can_execute_real_render: bool = False
    controlled_render_can_render: bool = False
    controlled_render_can_run_ffmpeg: bool = False
    controlled_render_can_spawn_process: bool = False
    controlled_render_can_write_media: bool = False
    controlled_render_output_created: bool = False
    controlled_render_output_path: str | None = None
    controlled_render_blocking_reasons: list[str] = field(default_factory=list)
    controlled_render_warnings: list[str] = field(default_factory=list)
    controlled_render_recommendation: str | None = None

    ffmpeg_capability_resolver_report: dict[str, Any] = field(default_factory=dict)
    ffmpeg_capability_status: str | None = None
    ffmpeg_path_hint: str | None = None
    ffprobe_path_hint: str | None = None
    ffmpeg_resolver_allow_tool_probe: bool = False
    ffmpeg_expected_path: str | None = None
    ffmpeg_tool_probe_attempted: bool = False
    ffmpeg_tool_probe_succeeded: bool = False
    ffmpeg_version: str | None = None
    ffprobe_version: str | None = None
    ffmpeg_capabilities: list[dict[str, Any]] = field(default_factory=list)
    ffmpeg_has_h264: bool = False
    ffmpeg_has_aac: bool = False
    ffmpeg_has_nvenc: bool = False
    ffmpeg_has_scale_filter: bool = False
    ffmpeg_has_concat_support: bool = False
    ffmpeg_has_loudnorm_filter: bool = False
    ffmpeg_can_prepare_real_render_tools: bool = False
    ffmpeg_can_render: bool = False
    ffmpeg_can_process_media: bool = False
    ffmpeg_can_write_media: bool = False
    ffmpeg_can_probe_media_files: bool = False
    ffmpeg_blocking_reasons: list[str] = field(default_factory=list)
    ffmpeg_warnings: list[str] = field(default_factory=list)
    ffmpeg_recommendation: str | None = None

    ffmpeg_command_assembly_report: dict[str, Any] = field(default_factory=dict)
    ffmpeg_command_assembly_status: str | None = None
    ffmpeg_command_assemblies: list[dict[str, Any]] = field(default_factory=list)
    ffmpeg_command_total_assemblies: int = 0
    ffmpeg_command_safe_assembly_count: int = 0
    ffmpeg_command_blocked_assembly_count: int = 0
    ffmpeg_command_dry_run_only: bool = True
    ffmpeg_command_assembly_only: bool = True
    ffmpeg_command_preview_only: bool = True
    ffmpeg_command_ready_for_controlled_execution_stage: bool = False
    ffmpeg_command_can_execute_commands: bool = False
    ffmpeg_command_can_spawn_process: bool = False
    ffmpeg_command_can_render: bool = False
    ffmpeg_command_can_write_media: bool = False
    ffmpeg_command_can_probe_media_files: bool = False
    ffmpeg_command_blocking_reasons: list[str] = field(default_factory=list)
    ffmpeg_command_warnings: list[str] = field(default_factory=list)
    ffmpeg_command_recommendation: str | None = None

    ffmpeg_execution_requested_mode: str = "dry_run"
    ffmpeg_execution_allow_real_render: bool = False
    ffmpeg_execution_allow_ffmpeg_execution: bool = False
    ffmpeg_execution_allow_process_spawn: bool = False
    ffmpeg_execution_allow_media_write: bool = False
    ffmpeg_execution_smoke_output_dir_hint: str | None = None
    ffmpeg_execution_smoke_duration_seconds: float = 1.0

    controlled_ffmpeg_execution_report: dict[str, Any] = field(default_factory=dict)
    controlled_ffmpeg_execution_status: str | None = None
    controlled_ffmpeg_execution_request: dict[str, Any] = field(default_factory=dict)
    controlled_ffmpeg_execution_result: dict[str, Any] = field(default_factory=dict)
    controlled_ffmpeg_dry_run_only: bool = True
    controlled_ffmpeg_smoke_test_only: bool = True
    controlled_ffmpeg_real_execution_requested: bool = False
    controlled_ffmpeg_real_execution_allowed: bool = False
    controlled_ffmpeg_real_execution_performed: bool = False
    controlled_ffmpeg_can_execute_full_render: bool = False
    controlled_ffmpeg_can_render_timeline: bool = False
    controlled_ffmpeg_can_process_user_media: bool = False
    controlled_ffmpeg_can_write_project_output: bool = False
    controlled_ffmpeg_can_spawn_process: bool = False
    controlled_ffmpeg_output_created: bool = False
    controlled_ffmpeg_output_path: str | None = None
    controlled_ffmpeg_blocking_reasons: list[str] = field(default_factory=list)
    controlled_ffmpeg_warnings: list[str] = field(default_factory=list)
    controlled_ffmpeg_recommendation: str | None = None

    output_format_contract_report: dict[str, Any] = field(default_factory=dict)
    output_format_contract_status: str | None = None
    output_format_selected_preset: str | None = None
    output_format_available_presets: list[str] = field(default_factory=list)
    output_format_selected_profile: str | None = None
    output_format_selected_platform: str | None = None
    output_format_selected_target_format: str | None = None
    output_video_spec: dict[str, Any] = field(default_factory=dict)
    output_audio_spec: dict[str, Any] = field(default_factory=dict)
    output_container_spec: dict[str, Any] = field(default_factory=dict)
    output_filename_hint: str | None = None
    output_safe_filename_hint: str | None = None
    output_path_hint: str | None = None
    output_can_prepare_output_format: bool = False
    output_can_render: bool = False
    output_can_write_project_output: bool = False
    output_can_process_user_media: bool = False
    output_can_execute_ffmpeg: bool = False
    output_dry_run_only: bool = True
    output_contract_only: bool = True
    output_format_blocking_reasons: list[str] = field(default_factory=list)
    output_format_warnings: list[str] = field(default_factory=list)
    output_format_recommendation: str | None = None

    render_verification_contract_report: dict[str, Any] = field(default_factory=dict)
    render_verification_contract_status: str | None = None
    render_verification_expected_spec: dict[str, Any] = field(default_factory=dict)
    render_verification_checks: list[dict[str, Any]] = field(default_factory=list)
    render_verification_probe_plan: dict[str, Any] = field(default_factory=dict)
    render_verification_total_checks: int = 0
    render_verification_planned_check_count: int = 0
    render_verification_runnable_smoke_check_count: int = 0
    render_verification_blocked_check_count: int = 0
    render_verification_contract_only: bool = True
    render_verification_dry_run_only: bool = True
    render_verification_smoke_probe_allowed: bool = False
    render_verification_project_output_probe_allowed: bool = False
    render_verification_can_verify_smoke_output: bool = False
    render_verification_can_verify_project_output: bool = False
    render_verification_can_probe_media_files: bool = False
    render_verification_can_render: bool = False
    render_verification_can_write_media: bool = False
    render_verification_blocking_reasons: list[str] = field(default_factory=list)
    render_verification_warnings: list[str] = field(default_factory=list)
    render_verification_recommendation: str | None = None

    render_verification_allow_smoke_probe: bool = False
    render_verification_allow_project_output_probe: bool = False
    render_verification_expected_duration_seconds: float | None = None
    render_verification_duration_tolerance_seconds: float = 1.0

    render_dashboard_delivery_package_report: dict[str, Any] = field(default_factory=dict)
    render_dashboard_delivery_package_status: str | None = None
    render_dashboard_delivery_cards: list[dict[str, Any]] = field(default_factory=list)
    render_dashboard_delivery_panels: list[dict[str, Any]] = field(default_factory=list)
    render_dashboard_delivery_actions: list[dict[str, Any]] = field(default_factory=list)
    render_dashboard_delivery_safety_summary: dict[str, Any] = field(default_factory=dict)
    render_dashboard_delivery_output_summary: dict[str, Any] = field(default_factory=dict)
    render_dashboard_delivery_verification_summary: dict[str, Any] = field(default_factory=dict)
    render_dashboard_delivery_ffmpeg_summary: dict[str, Any] = field(default_factory=dict)
    render_dashboard_delivery_total_warnings: int = 0
    render_dashboard_delivery_total_blocking_reasons: int = 0
    render_dashboard_delivery_dashboard_ready: bool = False
    render_dashboard_delivery_dashboard_only: bool = True
    render_dashboard_delivery_package_only: bool = True
    render_dashboard_delivery_can_write_dashboard_file: bool = False
    render_dashboard_delivery_can_move_video: bool = False
    render_dashboard_delivery_can_copy_output: bool = False
    render_dashboard_delivery_can_extract_thumbnail: bool = False
    render_dashboard_delivery_can_render: bool = False
    render_dashboard_delivery_can_run_ffmpeg: bool = False
    render_dashboard_delivery_can_run_ffprobe: bool = False
    render_dashboard_delivery_warnings: list[str] = field(default_factory=list)
    render_dashboard_delivery_blocking_reasons: list[str] = field(default_factory=list)
    render_dashboard_delivery_recommendation: str | None = None

    feedback_intake_report: dict[str, Any] = field(default_factory=dict)
    feedback_intake_status: str | None = None
    feedback_submissions: list[dict[str, Any]] = field(default_factory=list)
    feedback_submission_count: int = 0
    feedback_timestamp_feedback_count: int = 0
    feedback_positive_feedback_count: int = 0
    feedback_negative_feedback_count: int = 0
    feedback_neutral_feedback_count: int = 0
    feedback_average_video_score: float | None = None
    feedback_tags_summary: dict[str, int] = field(default_factory=dict)
    feedback_category_summary: dict[str, int] = field(default_factory=dict)
    feedback_review_required: bool = True
    feedback_ready_for_style_dna_update: bool = False
    feedback_can_update_style_dna: bool = False
    feedback_can_change_profile: bool = False
    feedback_can_change_cutting_rules: bool = False
    feedback_can_modify_timeline: bool = False
    feedback_can_trigger_render: bool = False
    feedback_can_publish: bool = False
    feedback_warnings: list[str] = field(default_factory=list)
    feedback_blocking_reasons: list[str] = field(default_factory=list)
    feedback_recommendation: str | None = None

    style_dna_feedback_update_report: dict[str, Any] = field(default_factory=dict)
    style_dna_feedback_update_status: str | None = None
    style_dna_update_draft: dict[str, Any] = field(default_factory=dict)
    style_dna_update_proposals: list[dict[str, Any]] = field(default_factory=list)
    style_dna_update_proposal_count: int = 0
    style_dna_update_confidence: float = 0.0
    style_dna_update_overfitting_risk: str | None = None
    style_dna_update_ready_for_human_review: bool = False
    style_dna_update_ready_for_later_apply: bool = False
    style_dna_update_can_write_style_dna: bool = False
    style_dna_update_can_update_profile: bool = False
    style_dna_update_can_change_cutting_rules: bool = False
    style_dna_update_can_modify_timeline: bool = False
    style_dna_update_can_trigger_render: bool = False
    style_dna_update_can_publish: bool = False
    style_dna_update_warnings: list[str] = field(default_factory=list)
    style_dna_update_blocking_reasons: list[str] = field(default_factory=list)
    style_dna_update_recommendation: str | None = None

    style_dna_review_gate_report: dict[str, Any] = field(default_factory=dict)
    style_dna_review_gate: dict[str, Any] = field(default_factory=dict)
    style_dna_review_status: str | None = None
    style_dna_review_requested_status: str = "pending_review"
    style_dna_reviewed_by: str | None = None
    style_dna_review_comment: str | None = None
    style_dna_review_requested_at: str | None = None
    style_dna_review_proposal_decisions: list[dict[str, Any]] = field(default_factory=list)
    style_dna_review_approved_proposal_count: int = 0
    style_dna_review_rejected_proposal_count: int = 0
    style_dna_review_needs_changes_count: int = 0
    style_dna_review_required: bool = True
    style_dna_review_ready_for_later_apply: bool = False
    style_dna_review_can_apply_style_dna: bool = False
    style_dna_review_can_write_style_dna: bool = False
    style_dna_review_can_update_profile: bool = False
    style_dna_review_can_change_cutting_rules: bool = False
    style_dna_review_can_modify_timeline: bool = False
    style_dna_review_can_trigger_render: bool = False
    style_dna_review_can_publish: bool = False
    style_dna_review_warnings: list[str] = field(default_factory=list)
    style_dna_review_blocking_reasons: list[str] = field(default_factory=list)
    style_dna_review_recommendation: str | None = None

    style_dna_apply_plan_report: dict[str, Any] = field(default_factory=dict)
    style_dna_apply_plan: dict[str, Any] = field(default_factory=dict)
    style_dna_apply_plan_status: str | None = None
    style_dna_apply_operations: list[dict[str, Any]] = field(default_factory=list)
    style_dna_apply_operation_count: int = 0
    style_dna_apply_approved_operation_count: int = 0
    style_dna_apply_skipped_operation_count: int = 0
    style_dna_apply_before_snapshot: dict[str, Any] = field(default_factory=dict)
    style_dna_apply_after_preview: dict[str, Any] = field(default_factory=dict)
    style_dna_apply_ready_for_future_file_write: bool = False
    style_dna_apply_can_write_style_dna: bool = False
    style_dna_apply_can_apply_style_dna: bool = False
    style_dna_apply_can_update_profile: bool = False
    style_dna_apply_can_change_cutting_rules: bool = False
    style_dna_apply_can_modify_timeline: bool = False
    style_dna_apply_can_trigger_render: bool = False
    style_dna_apply_can_publish: bool = False
    style_dna_apply_warnings: list[str] = field(default_factory=list)
    style_dna_apply_blocking_reasons: list[str] = field(default_factory=list)
    style_dna_apply_recommendation: str | None = None

    style_dna_persistence_gate_report: dict[str, Any] = field(default_factory=dict)
    style_dna_persistence_gate: dict[str, Any] = field(default_factory=dict)
    style_dna_persistence_status: str | None = None
    style_dna_persistence_requested_status: str = "pending_write_review"
    style_dna_persistence_approved_by: str | None = None
    style_dna_persistence_comment: str | None = None
    style_dna_persistence_requested_at: str | None = None
    style_dna_persistence_write_intent: dict[str, Any] = field(default_factory=dict)
    style_dna_persistence_write_preview_hash: str | None = None
    style_dna_persistence_target_path_hint: str | None = None
    style_dna_persistence_backup_required: bool = True
    style_dna_persistence_write_permission_ready_for_future: bool = False
    style_dna_persistence_can_write_style_dna: bool = False
    style_dna_persistence_can_apply_style_dna: bool = False
    style_dna_persistence_can_update_profile: bool = False
    style_dna_persistence_can_change_cutting_rules: bool = False
    style_dna_persistence_can_modify_timeline: bool = False
    style_dna_persistence_can_trigger_render: bool = False
    style_dna_persistence_can_publish: bool = False
    style_dna_persistence_warnings: list[str] = field(default_factory=list)
    style_dna_persistence_blocking_reasons: list[str] = field(default_factory=list)
    style_dna_persistence_recommendation: str | None = None

    learning_pattern_recognition_report: dict[str, Any] = field(default_factory=dict)
    learning_pattern_status: str | None = None
    learning_pattern_profile: str | None = None
    learning_pattern_feedback_sample_count: int = 0
    learning_pattern_trends: list[dict[str, Any]] = field(default_factory=list)
    learning_pattern_clusters: list[dict[str, Any]] = field(default_factory=list)
    learning_pattern_trend_count: int = 0
    learning_pattern_cluster_count: int = 0
    learning_pattern_top_positive_patterns: list[str] = field(default_factory=list)
    learning_pattern_top_negative_patterns: list[str] = field(default_factory=list)
    learning_pattern_repeated_issue_count: int = 0
    learning_pattern_repeated_success_count: int = 0
    learning_pattern_confidence: float = 0.0
    learning_pattern_overfitting_risk: str | None = None
    learning_pattern_ready_for_future_style_dna_proposal: bool = False
    learning_pattern_can_update_style_dna: bool = False
    learning_pattern_can_write_style_dna: bool = False
    learning_pattern_can_change_profile: bool = False
    learning_pattern_can_change_cutting_rules: bool = False
    learning_pattern_can_modify_timeline: bool = False
    learning_pattern_can_trigger_render: bool = False
    learning_pattern_can_publish: bool = False
    learning_pattern_warnings: list[str] = field(default_factory=list)
    learning_pattern_blocking_reasons: list[str] = field(default_factory=list)
    learning_pattern_recommendation: str | None = None

    feedback_history_snapshot: Any = field(default_factory=dict)
    style_dna_learning_history_snapshot: Any = field(default_factory=dict)
    learning_pattern_min_occurrences: int = 2
    learning_pattern_min_confidence: float = 0.50
    learning_pattern_requested_by: str | None = None
    learning_pattern_requested_at: str | None = None

    existing_style_dna_snapshot: dict[str, Any] = field(default_factory=dict)
    style_dna_profile_name: str | None = None
    style_dna_update_requested_by: str | None = None
    style_dna_update_requested_at: str | None = None
    style_dna_update_allow_file_write: bool = False
    style_dna_apply_requested_by: str | None = None
    style_dna_apply_requested_at: str | None = None
    style_dna_apply_allow_file_write: bool = False

    feedback_submission: dict[str, Any] = field(default_factory=dict)
    feedback_video_score: float | None = None
    feedback_comment: str | None = None
    feedback_timestamp_items: list[dict[str, Any]] = field(default_factory=list)
    feedback_tags: list[str] = field(default_factory=list)
    feedback_submitted_by: str | None = None
    feedback_submitted_at: str | None = None

    output_preset_requested: str | None = None
    output_platform_requested: str | None = None
    output_resolution_requested: str | None = None
    output_fps_requested: int | None = None
    output_codec_preference: str | None = None
    output_audio_lufs_requested: float | None = None
    output_container_requested: str | None = None

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

    @property
    def effective_publish_channel(self) -> ChannelType:
        return self.publish_target_channel or self.channel_type

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
            publish_target_channel=(
                ChannelType(data.get("publish_target_channel"))
                if data.get("publish_target_channel")
                else None
            ),
            raw_video_path=data.get("raw_video_path"),
            topic=data.get("topic"),
            title=data.get("title"),            
            pipeline_type=PipelineType(data["pipeline_type"]) if data.get("pipeline_type") else None,
            profile_id=data.get("profile_id"),
            quality_mode=data.get("quality_mode"),
            power_profile=str(data.get("power_profile") or "balanced"),
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
            reaction_shot_placement_report=dict(
                data.get("reaction_shot_placement_report") or {}
            ),
            reaction_shot_placement=dict(
                data.get("reaction_shot_placement") or {}
            ),
            reaction_shot_placement_status=data.get(
                "reaction_shot_placement_status"
            ),
            reaction_shot_candidates=list(
                data.get("reaction_shot_candidates") or []
            ),
            reaction_shot_placements=list(
                data.get("reaction_shot_placements") or []
            ),
            reaction_shot_total_candidates=int(
                data.get("reaction_shot_total_candidates", 0) or 0
            ),
            reaction_shot_total_placements=int(
                data.get("reaction_shot_total_placements", 0) or 0
            ),
            reaction_shot_best_placement_score=float(
                data.get("reaction_shot_best_placement_score", 0.0) or 0.0
            ),
            reaction_shot_missing_placeholder_count=int(
                data.get("reaction_shot_missing_placeholder_count", 0) or 0
            ),
            reaction_shot_review_required=bool(
                data.get("reaction_shot_review_required", True)
            ),
            reaction_shot_can_apply=False,
            reaction_shot_can_move_clip=False,
            reaction_shot_can_insert_clip=False,
            reaction_shot_can_trim=False,
            reaction_shot_can_extend=False,
            reaction_shot_can_reorder_timeline=False,
            reaction_shot_can_render=False,
            reaction_shot_blocking_reasons=list(
                data.get("reaction_shot_blocking_reasons") or []
            ),
            reaction_shot_warnings=list(
                data.get("reaction_shot_warnings") or []
            ),
            reaction_shot_recommendation=data.get(
                "reaction_shot_recommendation"
            ),
            but_therefore_story_report=dict(
                data.get("but_therefore_story_report") or {}
            ),
            but_therefore_story=dict(
                data.get("but_therefore_story") or {}
            ),
            but_therefore_story_status=data.get(
                "but_therefore_story_status"
            ),
            story_moments=list(data.get("story_moments") or []),
            story_transitions=list(data.get("story_transitions") or []),
            story_suggestions=list(data.get("story_suggestions") or []),
            story_total_moments=int(data.get("story_total_moments", 0) or 0),
            story_but_count=int(data.get("story_but_count", 0) or 0),
            story_therefore_count=int(data.get("story_therefore_count", 0) or 0),
            story_and_count=int(data.get("story_and_count", 0) or 0),
            story_reaction_count=int(data.get("story_reaction_count", 0) or 0),
            story_payoff_count=int(data.get("story_payoff_count", 0) or 0),
            story_strong_count=int(data.get("story_strong_count", 0) or 0),
            story_but_therefore_ratio=float(
                data.get("story_but_therefore_ratio", 0.0) or 0.0
            ),
            story_flow_score=float(data.get("story_flow_score", 0.0) or 0.0),
            story_and_streak_max=int(data.get("story_and_streak_max", 0) or 0),
            story_orphan_reaction_count=int(
                data.get("story_orphan_reaction_count", 0) or 0
            ),
            story_missing_payoff_count=int(
                data.get("story_missing_payoff_count", 0) or 0
            ),
            story_review_required=bool(
                data.get("story_review_required", True)
            ),
            story_can_apply_changes=False,
            story_can_remove_and_moments=False,
            story_can_reorder_timeline=False,
            story_can_trim=False,
            story_can_extend=False,
            story_can_render=False,
            story_blocking_reasons=list(
                data.get("story_blocking_reasons") or []
            ),
            story_warnings=list(data.get("story_warnings") or []),
            story_recommendation=data.get("story_recommendation"),
            final_quality_validation_report=dict(
                data.get("final_quality_validation_report") or {}
            ),
            final_quality_validator=dict(data.get("final_quality_validator") or {}),
            final_quality_validation_status=data.get(
                "final_quality_validation_status"
            ),
            final_quality_checks=list(data.get("final_quality_checks") or []),
            final_quality_suggestions=list(
                data.get("final_quality_suggestions") or []
            ),
            final_quality_audio_score=float(
                data.get("final_quality_audio_score", 0.0) or 0.0
            ),
            final_quality_video_score=float(
                data.get("final_quality_video_score", 0.0) or 0.0
            ),
            final_quality_story_score=float(
                data.get("final_quality_story_score", 0.0) or 0.0
            ),
            final_quality_pacing_score=float(
                data.get("final_quality_pacing_score", 0.0) or 0.0
            ),
            final_quality_safety_score=float(
                data.get("final_quality_safety_score", 1.0) or 1.0
            ),
            final_quality_overall_score=float(
                data.get("final_quality_overall_score", 0.0) or 0.0
            ),
            final_quality_passed_count=int(
                data.get("final_quality_passed_count", 0) or 0
            ),
            final_quality_warning_count=int(
                data.get("final_quality_warning_count", 0) or 0
            ),
            final_quality_blocking_count=int(
                data.get("final_quality_blocking_count", 0) or 0
            ),
            final_quality_review_required=bool(
                data.get("final_quality_review_required", True)
            ),
            final_quality_can_apply_fixes=False,
            final_quality_can_render=False,
            final_quality_can_execute_timeline=False,
            final_quality_can_reorder_timeline=False,
            final_quality_can_trim=False,
            final_quality_can_extend=False,
            final_quality_can_insert_effects=False,
            final_quality_blocking_reasons=list(
                data.get("final_quality_blocking_reasons") or []
            ),
            final_quality_warnings=list(data.get("final_quality_warnings") or []),
            final_quality_recommendation=data.get("final_quality_recommendation"),

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
            render_readiness_guard_report=dict(
                data.get("render_readiness_guard_report") or {}
            ),
            render_readiness_guard=dict(data.get("render_readiness_guard") or {}),
            render_readiness_status=data.get("render_readiness_status"),
            render_readiness_checks=list(data.get("render_readiness_checks") or []),
            render_readiness_total_checks=int(
                data.get("render_readiness_total_checks", 0) or 0
            ),
            render_readiness_passed_count=int(
                data.get("render_readiness_passed_count", 0) or 0
            ),
            render_readiness_warning_count=int(
                data.get("render_readiness_warning_count", 0) or 0
            ),
            render_readiness_blocking_count=int(
                data.get("render_readiness_blocking_count", 0) or 0
            ),
            render_readiness_review_required=bool(
                data.get("render_readiness_review_required", True)
            ),
            render_readiness_ready_for_next_render_stage=bool(
                data.get("render_readiness_ready_for_next_render_stage", False)
            ),
            render_readiness_can_start_render_pipeline=bool(
                data.get("render_readiness_can_start_render_pipeline", False)
            ),
            render_readiness_can_render=False,
            render_readiness_can_run_ffmpeg=False,
            render_readiness_can_execute_media_operations=False,
            render_readiness_can_apply_timeline=False,
            render_readiness_can_modify_media=False,
            render_readiness_blocking_reasons=list(
                data.get("render_readiness_blocking_reasons") or []
            ),
            render_readiness_warnings=list(data.get("render_readiness_warnings") or []),
            render_readiness_recommendation=data.get("render_readiness_recommendation"),

            render_plan_report=dict(data.get("render_plan_report") or {}),
            render_plan=dict(data.get("render_plan") or {}),
            render_plan_status=data.get("render_plan_status"),
            render_plan_sources=list(data.get("render_plan_sources") or []),
            render_plan_segments=list(data.get("render_plan_segments") or []),
            render_plan_output_targets=list(data.get("render_plan_output_targets") or []),
            render_plan_operation_intents=list(data.get("render_plan_operation_intents") or []),
            render_plan_total_segments=int(data.get("render_plan_total_segments", 0) or 0),
            render_plan_total_duration_seconds=float(
                data.get("render_plan_total_duration_seconds", 0.0) or 0.0
            ),
            render_plan_estimated_output_duration_seconds=float(
                data.get("render_plan_estimated_output_duration_seconds", 0.0) or 0.0
            ),
            render_plan_dry_run_only=bool(data.get("render_plan_dry_run_only", True)),
            render_plan_ready_for_renderer_contract=bool(
                data.get("render_plan_ready_for_renderer_contract", False)
            ),
            render_plan_can_execute_plan=False,
            render_plan_can_render=False,
            render_plan_can_run_ffmpeg=False,
            render_plan_can_write_media=False,
            render_plan_can_apply_timeline=False,
            render_plan_blocking_reasons=list(data.get("render_plan_blocking_reasons") or []),
            render_plan_warnings=list(data.get("render_plan_warnings") or []),
            render_plan_recommendation=data.get("render_plan_recommendation"),

            render_command_blueprint_report=dict(data.get("render_command_blueprint_report") or {}),
            render_command_blueprint=dict(data.get("render_command_blueprint") or {}),
            render_blueprint_status=data.get("render_blueprint_status"),
            render_blueprint_steps=list(data.get("render_blueprint_steps") or []),
            render_blueprint_total_steps=int(data.get("render_blueprint_total_steps", 0) or 0),
            render_blueprint_trim_step_count=int(data.get("render_blueprint_trim_step_count", 0) or 0),
            render_blueprint_concat_step_count=int(data.get("render_blueprint_concat_step_count", 0) or 0),
            render_blueprint_transition_step_count=int(data.get("render_blueprint_transition_step_count", 0) or 0),
            render_blueprint_audio_mix_step_count=int(data.get("render_blueprint_audio_mix_step_count", 0) or 0),
            render_blueprint_censor_sfx_step_count=int(data.get("render_blueprint_censor_sfx_step_count", 0) or 0),
            render_blueprint_subtitle_step_count=int(data.get("render_blueprint_subtitle_step_count", 0) or 0),
            render_blueprint_encode_step_count=int(data.get("render_blueprint_encode_step_count", 0) or 0),
            render_blueprint_dry_run_only=bool(data.get("render_blueprint_dry_run_only", True)),
            render_blueprint_non_executable=bool(data.get("render_blueprint_non_executable", True)),
            render_blueprint_ready_for_renderer_implementation=bool(
                data.get("render_blueprint_ready_for_renderer_implementation", False)
            ),
            render_blueprint_can_execute_contract=False,
            render_blueprint_can_render=False,
            render_blueprint_can_run_ffmpeg=False,
            render_blueprint_can_spawn_process=False,
            render_blueprint_can_write_media=False,
            render_blueprint_blocking_reasons=list(data.get("render_blueprint_blocking_reasons") or []),
            render_blueprint_warnings=list(data.get("render_blueprint_warnings") or []),
            render_blueprint_recommendation=data.get("render_blueprint_recommendation"),

            render_asset_manifest_report=dict(data.get("render_asset_manifest_report") or {}),
            render_asset_manifest=dict(data.get("render_asset_manifest") or {}),
            render_asset_manifest_status=data.get("render_asset_manifest_status"),
            render_asset_references=list(data.get("render_asset_references") or []),
            render_output_path_plans=list(data.get("render_output_path_plans") or []),
            render_asset_total_assets=int(data.get("render_asset_total_assets", 0) or 0),
            render_asset_required_count=int(data.get("render_asset_required_count", 0) or 0),
            render_asset_missing_required_hint_count=int(
                data.get("render_asset_missing_required_hint_count", 0) or 0
            ),
            render_asset_unsafe_path_count=int(data.get("render_asset_unsafe_path_count", 0) or 0),
            render_asset_output_plan_count=int(data.get("render_asset_output_plan_count", 0) or 0),
            render_asset_dry_run_only=bool(data.get("render_asset_dry_run_only", True)),
            render_asset_manifest_only=bool(data.get("render_asset_manifest_only", True)),
            render_asset_paths_are_hints_only=bool(
                data.get("render_asset_paths_are_hints_only", True)
            ),
            render_asset_can_create_directories=False,
            render_asset_can_write_files=False,
            render_asset_can_open_media=False,
            render_asset_can_render=False,
            render_asset_can_run_ffmpeg=False,
            render_asset_blocking_reasons=list(data.get("render_asset_blocking_reasons") or []),
            render_asset_warnings=list(data.get("render_asset_warnings") or []),
            render_asset_recommendation=data.get("render_asset_recommendation"),

            render_execution_permission_report=dict(data.get("render_execution_permission_report") or {}),
            render_execution_permission_gate=dict(data.get("render_execution_permission_gate") or {}),
            render_execution_permission_status=data.get("render_execution_permission_status"),
            render_execution_permission_checks=list(data.get("render_execution_permission_checks") or []),
            render_execution_permission_total_checks=int(
                data.get("render_execution_permission_total_checks", 0) or 0
            ),
            render_execution_permission_passed_count=int(
                data.get("render_execution_permission_passed_count", 0) or 0
            ),
            render_execution_permission_warning_count=int(
                data.get("render_execution_permission_warning_count", 0) or 0
            ),
            render_execution_permission_blocking_count=int(
                data.get("render_execution_permission_blocking_count", 0) or 0
            ),
            render_execution_permission_review_required=bool(
                data.get("render_execution_permission_review_required", True)
            ),
            render_execution_ready_for_real_render_stage=bool(
                data.get("render_execution_ready_for_real_render_stage", False)
            ),
            render_execution_can_prepare_real_render_execution=bool(
                data.get("render_execution_can_prepare_real_render_execution", False)
            ),
            render_execution_can_render=False,
            render_execution_can_run_ffmpeg=False,
            render_execution_can_spawn_process=False,
            render_execution_can_write_media=False,
            render_execution_can_apply_timeline=False,
            render_execution_human_approved=bool(
                data.get("render_execution_human_approved", False)
            ),
            render_execution_requested_status=data.get("render_execution_requested_status"),
            render_execution_approved_by=data.get("render_execution_approved_by"),
            render_execution_approved_at=data.get("render_execution_approved_at"),
            render_execution_approval_reason=data.get("render_execution_approval_reason"),
            render_execution_rejected_by=data.get("render_execution_rejected_by"),
            render_execution_rejection_reason=data.get("render_execution_rejection_reason"),
            render_execution_blocking_reasons=list(data.get("render_execution_blocking_reasons") or []),
            render_execution_warnings=list(data.get("render_execution_warnings") or []),
            render_execution_recommendation=data.get("render_execution_recommendation"),

            render_execution_requested_mode=str(
                data.get("render_execution_requested_mode", "dry_run") or "dry_run"
            ),
            render_execution_allow_real_render=bool(
                data.get("render_execution_allow_real_render", False)
            ),
            render_execution_allow_ffmpeg=bool(
                data.get("render_execution_allow_ffmpeg", False)
            ),
            render_execution_allow_process_spawn=bool(
                data.get("render_execution_allow_process_spawn", False)
            ),
            render_execution_allow_media_write=bool(
                data.get("render_execution_allow_media_write", False)
            ),

            controlled_render_executor_report=dict(data.get("controlled_render_executor_report") or {}),
            controlled_render_executor=dict(data.get("controlled_render_executor") or {}),
            controlled_render_executor_status=data.get("controlled_render_executor_status"),
            controlled_render_execution_request=dict(data.get("controlled_render_execution_request") or {}),
            controlled_render_execution_steps=list(data.get("controlled_render_execution_steps") or []),
            controlled_render_total_steps=int(data.get("controlled_render_total_steps", 0) or 0),
            controlled_render_planned_step_count=int(
                data.get("controlled_render_planned_step_count", 0) or 0
            ),
            controlled_render_executed_step_count=int(
                data.get("controlled_render_executed_step_count", 0) or 0
            ),
            controlled_render_skipped_step_count=int(
                data.get("controlled_render_skipped_step_count", 0) or 0
            ),
            controlled_render_dry_run_only=bool(
                data.get("controlled_render_dry_run_only", True)
            ),
            controlled_render_real_render_requested=bool(
                data.get("controlled_render_real_render_requested", False)
            ),
            controlled_render_real_render_allowed=False,
            controlled_render_can_execute_real_render=False,
            controlled_render_can_render=False,
            controlled_render_can_run_ffmpeg=False,
            controlled_render_can_spawn_process=False,
            controlled_render_can_write_media=False,
            controlled_render_output_created=False,
            controlled_render_output_path=None,
            controlled_render_blocking_reasons=list(
                data.get("controlled_render_blocking_reasons") or []
            ),
            controlled_render_warnings=list(data.get("controlled_render_warnings") or []),
            controlled_render_recommendation=data.get("controlled_render_recommendation"),

            ffmpeg_capability_resolver_report=dict(
                data.get("ffmpeg_capability_resolver_report") or {}
            ),
            ffmpeg_capability_status=data.get("ffmpeg_capability_status"),
            ffmpeg_path_hint=data.get("ffmpeg_path_hint"),
            ffprobe_path_hint=data.get("ffprobe_path_hint"),
            ffmpeg_resolver_allow_tool_probe=bool(
                data.get("ffmpeg_resolver_allow_tool_probe", False)
            ),
            ffmpeg_expected_path=data.get("ffmpeg_expected_path"),
            ffmpeg_tool_probe_attempted=bool(
                data.get("ffmpeg_tool_probe_attempted", False)
            ),
            ffmpeg_tool_probe_succeeded=bool(
                data.get("ffmpeg_tool_probe_succeeded", False)
            ),
            ffmpeg_version=data.get("ffmpeg_version"),
            ffprobe_version=data.get("ffprobe_version"),
            ffmpeg_capabilities=list(data.get("ffmpeg_capabilities") or []),
            ffmpeg_has_h264=bool(data.get("ffmpeg_has_h264", False)),
            ffmpeg_has_aac=bool(data.get("ffmpeg_has_aac", False)),
            ffmpeg_has_nvenc=bool(data.get("ffmpeg_has_nvenc", False)),
            ffmpeg_has_scale_filter=bool(
                data.get("ffmpeg_has_scale_filter", False)
            ),
            ffmpeg_has_concat_support=bool(
                data.get("ffmpeg_has_concat_support", False)
            ),
            ffmpeg_has_loudnorm_filter=bool(
                data.get("ffmpeg_has_loudnorm_filter", False)
            ),
            ffmpeg_can_prepare_real_render_tools=bool(
                data.get("ffmpeg_can_prepare_real_render_tools", False)
            ),
            ffmpeg_can_render=False,
            ffmpeg_can_process_media=False,
            ffmpeg_can_write_media=False,
            ffmpeg_can_probe_media_files=False,
            ffmpeg_blocking_reasons=list(data.get("ffmpeg_blocking_reasons") or []),
            ffmpeg_warnings=list(data.get("ffmpeg_warnings") or []),
            ffmpeg_recommendation=data.get("ffmpeg_recommendation"),

            ffmpeg_command_assembly_report=dict(
                data.get("ffmpeg_command_assembly_report") or {}
            ),
            ffmpeg_command_assembly_status=data.get("ffmpeg_command_assembly_status"),
            ffmpeg_command_assemblies=list(data.get("ffmpeg_command_assemblies") or []),
            ffmpeg_command_total_assemblies=int(
                data.get("ffmpeg_command_total_assemblies", 0) or 0
            ),
            ffmpeg_command_safe_assembly_count=int(
                data.get("ffmpeg_command_safe_assembly_count", 0) or 0
            ),
            ffmpeg_command_blocked_assembly_count=int(
                data.get("ffmpeg_command_blocked_assembly_count", 0) or 0
            ),
            ffmpeg_command_dry_run_only=bool(
                data.get("ffmpeg_command_dry_run_only", True)
            ),
            ffmpeg_command_assembly_only=bool(
                data.get("ffmpeg_command_assembly_only", True)
            ),
            ffmpeg_command_preview_only=bool(
                data.get("ffmpeg_command_preview_only", True)
            ),
            ffmpeg_command_ready_for_controlled_execution_stage=bool(
                data.get("ffmpeg_command_ready_for_controlled_execution_stage", False)
            ),
            ffmpeg_command_can_execute_commands=False,
            ffmpeg_command_can_spawn_process=False,
            ffmpeg_command_can_render=False,
            ffmpeg_command_can_write_media=False,
            ffmpeg_command_can_probe_media_files=False,
            ffmpeg_command_blocking_reasons=list(
                data.get("ffmpeg_command_blocking_reasons") or []
            ),
            ffmpeg_command_warnings=list(data.get("ffmpeg_command_warnings") or []),
            ffmpeg_command_recommendation=data.get("ffmpeg_command_recommendation"),

            ffmpeg_execution_requested_mode=str(
                data.get("ffmpeg_execution_requested_mode", "dry_run") or "dry_run"
            ),
            ffmpeg_execution_allow_real_render=bool(
                data.get("ffmpeg_execution_allow_real_render", False)
            ),
            ffmpeg_execution_allow_ffmpeg_execution=bool(
                data.get("ffmpeg_execution_allow_ffmpeg_execution", False)
            ),
            ffmpeg_execution_allow_process_spawn=bool(
                data.get("ffmpeg_execution_allow_process_spawn", False)
            ),
            ffmpeg_execution_allow_media_write=bool(
                data.get("ffmpeg_execution_allow_media_write", False)
            ),
            ffmpeg_execution_smoke_output_dir_hint=data.get(
                "ffmpeg_execution_smoke_output_dir_hint"
            ),
            ffmpeg_execution_smoke_duration_seconds=float(
                data.get("ffmpeg_execution_smoke_duration_seconds", 1.0) or 1.0
            ),

            controlled_ffmpeg_execution_report=dict(
                data.get("controlled_ffmpeg_execution_report") or {}
            ),
            controlled_ffmpeg_execution_status=data.get(
                "controlled_ffmpeg_execution_status"
            ),
            controlled_ffmpeg_execution_request=dict(
                data.get("controlled_ffmpeg_execution_request") or {}
            ),
            controlled_ffmpeg_execution_result=dict(
                data.get("controlled_ffmpeg_execution_result") or {}
            ),
            controlled_ffmpeg_dry_run_only=bool(
                data.get("controlled_ffmpeg_dry_run_only", True)
            ),
            controlled_ffmpeg_smoke_test_only=bool(
                data.get("controlled_ffmpeg_smoke_test_only", True)
            ),
            controlled_ffmpeg_real_execution_requested=bool(
                data.get("controlled_ffmpeg_real_execution_requested", False)
            ),
            controlled_ffmpeg_real_execution_allowed=bool(
                data.get("controlled_ffmpeg_real_execution_allowed", False)
            ),
            controlled_ffmpeg_real_execution_performed=bool(
                data.get("controlled_ffmpeg_real_execution_performed", False)
            ),
            controlled_ffmpeg_can_execute_full_render=False,
            controlled_ffmpeg_can_render_timeline=False,
            controlled_ffmpeg_can_process_user_media=False,
            controlled_ffmpeg_can_write_project_output=False,
            controlled_ffmpeg_can_spawn_process=bool(
                data.get("controlled_ffmpeg_can_spawn_process", False)
            ),
            controlled_ffmpeg_output_created=bool(
                data.get("controlled_ffmpeg_output_created", False)
            ),
            controlled_ffmpeg_output_path=data.get("controlled_ffmpeg_output_path"),
            controlled_ffmpeg_blocking_reasons=list(
                data.get("controlled_ffmpeg_blocking_reasons") or []
            ),
            controlled_ffmpeg_warnings=list(
                data.get("controlled_ffmpeg_warnings") or []
            ),
            controlled_ffmpeg_recommendation=data.get(
                "controlled_ffmpeg_recommendation"
            ),

            output_format_contract_report=dict(
                data.get("output_format_contract_report") or {}
            ),
            output_format_contract_status=data.get("output_format_contract_status"),
            output_format_selected_preset=data.get("output_format_selected_preset"),
            output_format_available_presets=list(
                data.get("output_format_available_presets") or []
            ),
            output_format_selected_profile=data.get("output_format_selected_profile"),
            output_format_selected_platform=data.get("output_format_selected_platform"),
            output_format_selected_target_format=data.get(
                "output_format_selected_target_format"
            ),
            output_video_spec=dict(data.get("output_video_spec") or {}),
            output_audio_spec=dict(data.get("output_audio_spec") or {}),
            output_container_spec=dict(data.get("output_container_spec") or {}),
            output_filename_hint=data.get("output_filename_hint"),
            output_safe_filename_hint=data.get("output_safe_filename_hint"),
            output_path_hint=data.get("output_path_hint"),
            output_can_prepare_output_format=bool(
                data.get("output_can_prepare_output_format", False)
            ),
            output_can_render=False,
            output_can_write_project_output=False,
            output_can_process_user_media=False,
            output_can_execute_ffmpeg=False,
            output_dry_run_only=bool(data.get("output_dry_run_only", True)),
            output_contract_only=bool(data.get("output_contract_only", True)),
            output_format_blocking_reasons=list(
                data.get("output_format_blocking_reasons") or []
            ),
            output_format_warnings=list(data.get("output_format_warnings") or []),
            output_format_recommendation=data.get("output_format_recommendation"),

            render_verification_contract_report=dict(
                data.get("render_verification_contract_report") or {}
            ),
            render_verification_contract_status=data.get(
                "render_verification_contract_status"
            ),
            render_verification_expected_spec=dict(
                data.get("render_verification_expected_spec") or {}
            ),
            render_verification_checks=list(
                data.get("render_verification_checks") or []
            ),
            render_verification_probe_plan=dict(
                data.get("render_verification_probe_plan") or {}
            ),
            render_verification_total_checks=int(
                data.get("render_verification_total_checks", 0) or 0
            ),
            render_verification_planned_check_count=int(
                data.get("render_verification_planned_check_count", 0) or 0
            ),
            render_verification_runnable_smoke_check_count=int(
                data.get("render_verification_runnable_smoke_check_count", 0) or 0
            ),
            render_verification_blocked_check_count=int(
                data.get("render_verification_blocked_check_count", 0) or 0
            ),
            render_verification_contract_only=bool(
                data.get("render_verification_contract_only", True)
            ),
            render_verification_dry_run_only=bool(
                data.get("render_verification_dry_run_only", True)
            ),
            render_verification_smoke_probe_allowed=bool(
                data.get("render_verification_smoke_probe_allowed", False)
            ),
            render_verification_project_output_probe_allowed=False,
            render_verification_can_verify_smoke_output=bool(
                data.get("render_verification_can_verify_smoke_output", False)
            ),
            render_verification_can_verify_project_output=False,
            render_verification_can_probe_media_files=False,
            render_verification_can_render=False,
            render_verification_can_write_media=False,
            render_verification_blocking_reasons=list(
                data.get("render_verification_blocking_reasons") or []
            ),
            render_verification_warnings=list(
                data.get("render_verification_warnings") or []
            ),
            render_verification_recommendation=data.get(
                "render_verification_recommendation"
            ),
            render_verification_allow_smoke_probe=bool(
                data.get("render_verification_allow_smoke_probe", False)
            ),
            render_verification_allow_project_output_probe=bool(
                data.get("render_verification_allow_project_output_probe", False)
            ),
            render_verification_expected_duration_seconds=(
                float(data["render_verification_expected_duration_seconds"])
                if data.get("render_verification_expected_duration_seconds") is not None
                else None
            ),
            render_verification_duration_tolerance_seconds=float(
                data.get("render_verification_duration_tolerance_seconds", 1.0) or 1.0
            ),

            render_dashboard_delivery_package_report=dict(
                data.get("render_dashboard_delivery_package_report") or {}
            ),
            render_dashboard_delivery_package_status=data.get(
                "render_dashboard_delivery_package_status"
            ),
            render_dashboard_delivery_cards=list(
                data.get("render_dashboard_delivery_cards") or []
            ),
            render_dashboard_delivery_panels=list(
                data.get("render_dashboard_delivery_panels") or []
            ),
            render_dashboard_delivery_actions=list(
                data.get("render_dashboard_delivery_actions") or []
            ),
            render_dashboard_delivery_safety_summary=dict(
                data.get("render_dashboard_delivery_safety_summary") or {}
            ),
            render_dashboard_delivery_output_summary=dict(
                data.get("render_dashboard_delivery_output_summary") or {}
            ),
            render_dashboard_delivery_verification_summary=dict(
                data.get("render_dashboard_delivery_verification_summary") or {}
            ),
            render_dashboard_delivery_ffmpeg_summary=dict(
                data.get("render_dashboard_delivery_ffmpeg_summary") or {}
            ),
            render_dashboard_delivery_total_warnings=int(
                data.get("render_dashboard_delivery_total_warnings", 0) or 0
            ),
            render_dashboard_delivery_total_blocking_reasons=int(
                data.get("render_dashboard_delivery_total_blocking_reasons", 0) or 0
            ),
            render_dashboard_delivery_dashboard_ready=bool(
                data.get("render_dashboard_delivery_dashboard_ready", False)
            ),
            render_dashboard_delivery_dashboard_only=bool(
                data.get("render_dashboard_delivery_dashboard_only", True)
            ),
            render_dashboard_delivery_package_only=bool(
                data.get("render_dashboard_delivery_package_only", True)
            ),
            render_dashboard_delivery_can_write_dashboard_file=False,
            render_dashboard_delivery_can_move_video=False,
            render_dashboard_delivery_can_copy_output=False,
            render_dashboard_delivery_can_extract_thumbnail=False,
            render_dashboard_delivery_can_render=False,
            render_dashboard_delivery_can_run_ffmpeg=False,
            render_dashboard_delivery_can_run_ffprobe=False,
            render_dashboard_delivery_warnings=list(
                data.get("render_dashboard_delivery_warnings") or []
            ),
            render_dashboard_delivery_blocking_reasons=list(
                data.get("render_dashboard_delivery_blocking_reasons") or []
            ),
            render_dashboard_delivery_recommendation=data.get(
                "render_dashboard_delivery_recommendation"
            ),

            feedback_intake_report=dict(data.get("feedback_intake_report") or {}),
            feedback_intake_status=data.get("feedback_intake_status"),
            feedback_submissions=list(data.get("feedback_submissions") or []),
            feedback_submission_count=int(
                data.get("feedback_submission_count", 0) or 0
            ),
            feedback_timestamp_feedback_count=int(
                data.get("feedback_timestamp_feedback_count", 0) or 0
            ),
            feedback_positive_feedback_count=int(
                data.get("feedback_positive_feedback_count", 0) or 0
            ),
            feedback_negative_feedback_count=int(
                data.get("feedback_negative_feedback_count", 0) or 0
            ),
            feedback_neutral_feedback_count=int(
                data.get("feedback_neutral_feedback_count", 0) or 0
            ),
            feedback_average_video_score=(
                float(data["feedback_average_video_score"])
                if data.get("feedback_average_video_score") is not None
                else None
            ),
            feedback_tags_summary=dict(data.get("feedback_tags_summary") or {}),
            feedback_category_summary=dict(data.get("feedback_category_summary") or {}),
            feedback_review_required=bool(
                data.get("feedback_review_required", True)
            ),
            feedback_ready_for_style_dna_update=bool(
                data.get("feedback_ready_for_style_dna_update", False)
            ),
            feedback_can_update_style_dna=False,
            feedback_can_change_profile=False,
            feedback_can_change_cutting_rules=False,
            feedback_can_modify_timeline=False,
            feedback_can_trigger_render=False,
            feedback_can_publish=False,
            feedback_warnings=list(data.get("feedback_warnings") or []),
            feedback_blocking_reasons=list(
                data.get("feedback_blocking_reasons") or []
            ),
            feedback_recommendation=data.get("feedback_recommendation"),

            style_dna_feedback_update_report=dict(
                data.get("style_dna_feedback_update_report") or {}
            ),
            style_dna_feedback_update_status=data.get(
                "style_dna_feedback_update_status"
            ),
            style_dna_update_draft=dict(data.get("style_dna_update_draft") or {}),
            style_dna_update_proposals=list(
                data.get("style_dna_update_proposals") or []
            ),
            style_dna_update_proposal_count=int(
                data.get("style_dna_update_proposal_count", 0) or 0
            ),
            style_dna_update_confidence=float(
                data.get("style_dna_update_confidence", 0.0) or 0.0
            ),
            style_dna_update_overfitting_risk=data.get(
                "style_dna_update_overfitting_risk"
            ),
            style_dna_update_ready_for_human_review=bool(
                data.get("style_dna_update_ready_for_human_review", False)
            ),
            style_dna_update_ready_for_later_apply=bool(
                data.get("style_dna_update_ready_for_later_apply", False)
            ),
            style_dna_update_can_write_style_dna=False,
            style_dna_update_can_update_profile=False,
            style_dna_update_can_change_cutting_rules=False,
            style_dna_update_can_modify_timeline=False,
            style_dna_update_can_trigger_render=False,
            style_dna_update_can_publish=False,
            style_dna_update_warnings=list(
                data.get("style_dna_update_warnings") or []
            ),
            style_dna_update_blocking_reasons=list(
                data.get("style_dna_update_blocking_reasons") or []
            ),
            style_dna_update_recommendation=data.get(
                "style_dna_update_recommendation"
            ),

            style_dna_review_gate_report=dict(
                data.get("style_dna_review_gate_report") or {}
            ),
            style_dna_review_gate=dict(data.get("style_dna_review_gate") or {}),
            style_dna_review_status=data.get("style_dna_review_status"),
            style_dna_review_requested_status=str(
                data.get("style_dna_review_requested_status") or "pending_review"
            ),
            style_dna_reviewed_by=data.get("style_dna_reviewed_by"),
            style_dna_review_comment=data.get("style_dna_review_comment"),
            style_dna_review_requested_at=data.get("style_dna_review_requested_at"),
            style_dna_review_proposal_decisions=list(
                data.get("style_dna_review_proposal_decisions") or []
            ),
            style_dna_review_approved_proposal_count=int(
                data.get("style_dna_review_approved_proposal_count", 0) or 0
            ),
            style_dna_review_rejected_proposal_count=int(
                data.get("style_dna_review_rejected_proposal_count", 0) or 0
            ),
            style_dna_review_needs_changes_count=int(
                data.get("style_dna_review_needs_changes_count", 0) or 0
            ),
            style_dna_review_required=bool(
                data.get("style_dna_review_required", True)
            ),
            style_dna_review_ready_for_later_apply=bool(
                data.get("style_dna_review_ready_for_later_apply", False)
            ),
            style_dna_review_can_apply_style_dna=False,
            style_dna_review_can_write_style_dna=False,
            style_dna_review_can_update_profile=False,
            style_dna_review_can_change_cutting_rules=False,
            style_dna_review_can_modify_timeline=False,
            style_dna_review_can_trigger_render=False,
            style_dna_review_can_publish=False,
            style_dna_review_warnings=list(
                data.get("style_dna_review_warnings") or []
            ),
            style_dna_review_blocking_reasons=list(
                data.get("style_dna_review_blocking_reasons") or []
            ),
            style_dna_review_recommendation=data.get(
                "style_dna_review_recommendation"
            ),

            style_dna_apply_plan_report=dict(
                data.get("style_dna_apply_plan_report") or {}
            ),
            style_dna_apply_plan=dict(data.get("style_dna_apply_plan") or {}),
            style_dna_apply_plan_status=data.get("style_dna_apply_plan_status"),
            style_dna_apply_operations=list(
                data.get("style_dna_apply_operations") or []
            ),
            style_dna_apply_operation_count=int(
                data.get("style_dna_apply_operation_count", 0) or 0
            ),
            style_dna_apply_approved_operation_count=int(
                data.get("style_dna_apply_approved_operation_count", 0) or 0
            ),
            style_dna_apply_skipped_operation_count=int(
                data.get("style_dna_apply_skipped_operation_count", 0) or 0
            ),
            style_dna_apply_before_snapshot=dict(
                data.get("style_dna_apply_before_snapshot") or {}
            ),
            style_dna_apply_after_preview=dict(
                data.get("style_dna_apply_after_preview") or {}
            ),
            style_dna_apply_ready_for_future_file_write=bool(
                data.get("style_dna_apply_ready_for_future_file_write", False)
            ),
            style_dna_apply_can_write_style_dna=False,
            style_dna_apply_can_apply_style_dna=False,
            style_dna_apply_can_update_profile=False,
            style_dna_apply_can_change_cutting_rules=False,
            style_dna_apply_can_modify_timeline=False,
            style_dna_apply_can_trigger_render=False,
            style_dna_apply_can_publish=False,
            style_dna_apply_warnings=list(data.get("style_dna_apply_warnings") or []),
            style_dna_apply_blocking_reasons=list(
                data.get("style_dna_apply_blocking_reasons") or []
            ),
            style_dna_apply_recommendation=data.get("style_dna_apply_recommendation"),

            style_dna_persistence_gate_report=dict(
                data.get("style_dna_persistence_gate_report") or {}
            ),
            style_dna_persistence_gate=dict(
                data.get("style_dna_persistence_gate") or {}
            ),
            style_dna_persistence_status=data.get("style_dna_persistence_status"),
            style_dna_persistence_requested_status=str(
                data.get("style_dna_persistence_requested_status")
                or "pending_write_review"
            ),
            style_dna_persistence_approved_by=data.get(
                "style_dna_persistence_approved_by"
            ),
            style_dna_persistence_comment=data.get("style_dna_persistence_comment"),
            style_dna_persistence_requested_at=data.get(
                "style_dna_persistence_requested_at"
            ),
            style_dna_persistence_write_intent=dict(
                data.get("style_dna_persistence_write_intent") or {}
            ),
            style_dna_persistence_write_preview_hash=data.get(
                "style_dna_persistence_write_preview_hash"
            ),
            style_dna_persistence_target_path_hint=data.get(
                "style_dna_persistence_target_path_hint"
            ),
            style_dna_persistence_backup_required=bool(
                data.get("style_dna_persistence_backup_required", True)
            ),
            style_dna_persistence_write_permission_ready_for_future=bool(
                data.get(
                    "style_dna_persistence_write_permission_ready_for_future",
                    False,
                )
            ),
            style_dna_persistence_can_write_style_dna=False,
            style_dna_persistence_can_apply_style_dna=False,
            style_dna_persistence_can_update_profile=False,
            style_dna_persistence_can_change_cutting_rules=False,
            style_dna_persistence_can_modify_timeline=False,
            style_dna_persistence_can_trigger_render=False,
            style_dna_persistence_can_publish=False,
            style_dna_persistence_warnings=list(
                data.get("style_dna_persistence_warnings") or []
            ),
            style_dna_persistence_blocking_reasons=list(
                data.get("style_dna_persistence_blocking_reasons") or []
            ),
            style_dna_persistence_recommendation=data.get(
                "style_dna_persistence_recommendation"
            ),

            learning_pattern_recognition_report=dict(
                data.get("learning_pattern_recognition_report") or {}
            ),
            learning_pattern_status=data.get("learning_pattern_status"),
            learning_pattern_profile=data.get("learning_pattern_profile"),
            learning_pattern_feedback_sample_count=int(
                data.get("learning_pattern_feedback_sample_count", 0) or 0
            ),
            learning_pattern_trends=list(data.get("learning_pattern_trends") or []),
            learning_pattern_clusters=list(data.get("learning_pattern_clusters") or []),
            learning_pattern_trend_count=int(
                data.get("learning_pattern_trend_count", 0) or 0
            ),
            learning_pattern_cluster_count=int(
                data.get("learning_pattern_cluster_count", 0) or 0
            ),
            learning_pattern_top_positive_patterns=list(
                data.get("learning_pattern_top_positive_patterns") or []
            ),
            learning_pattern_top_negative_patterns=list(
                data.get("learning_pattern_top_negative_patterns") or []
            ),
            learning_pattern_repeated_issue_count=int(
                data.get("learning_pattern_repeated_issue_count", 0) or 0
            ),
            learning_pattern_repeated_success_count=int(
                data.get("learning_pattern_repeated_success_count", 0) or 0
            ),
            learning_pattern_confidence=float(
                data.get("learning_pattern_confidence", 0.0) or 0.0
            ),
            learning_pattern_overfitting_risk=data.get(
                "learning_pattern_overfitting_risk"
            ),
            learning_pattern_ready_for_future_style_dna_proposal=bool(
                data.get(
                    "learning_pattern_ready_for_future_style_dna_proposal",
                    False,
                )
            ),
            learning_pattern_can_update_style_dna=False,
            learning_pattern_can_write_style_dna=False,
            learning_pattern_can_change_profile=False,
            learning_pattern_can_change_cutting_rules=False,
            learning_pattern_can_modify_timeline=False,
            learning_pattern_can_trigger_render=False,
            learning_pattern_can_publish=False,
            learning_pattern_warnings=list(data.get("learning_pattern_warnings") or []),
            learning_pattern_blocking_reasons=list(
                data.get("learning_pattern_blocking_reasons") or []
            ),
            learning_pattern_recommendation=data.get("learning_pattern_recommendation"),

            feedback_history_snapshot=(
                data.get("feedback_history_snapshot")
                if isinstance(data.get("feedback_history_snapshot"), (dict, list))
                else {}
            ),
            style_dna_learning_history_snapshot=(
                data.get("style_dna_learning_history_snapshot")
                if isinstance(
                    data.get("style_dna_learning_history_snapshot"),
                    (dict, list),
                )
                else {}
            ),
            learning_pattern_min_occurrences=int(
                data.get("learning_pattern_min_occurrences", 2) or 2
            ),
            learning_pattern_min_confidence=float(
                data.get("learning_pattern_min_confidence", 0.50) or 0.50
            ),
            learning_pattern_requested_by=data.get("learning_pattern_requested_by"),
            learning_pattern_requested_at=data.get("learning_pattern_requested_at"),

            existing_style_dna_snapshot=dict(
                data.get("existing_style_dna_snapshot") or {}
            ),
            style_dna_profile_name=data.get("style_dna_profile_name"),
            style_dna_update_requested_by=data.get(
                "style_dna_update_requested_by"
            ),
            style_dna_update_requested_at=data.get(
                "style_dna_update_requested_at"
            ),
            style_dna_update_allow_file_write=bool(
                data.get("style_dna_update_allow_file_write", False)
            ),
            style_dna_apply_requested_by=data.get("style_dna_apply_requested_by"),
            style_dna_apply_requested_at=data.get("style_dna_apply_requested_at"),
            style_dna_apply_allow_file_write=bool(
                data.get("style_dna_apply_allow_file_write", False)
            ),

            feedback_submission=dict(data.get("feedback_submission") or {}),
            feedback_video_score=(
                float(data["feedback_video_score"])
                if data.get("feedback_video_score") is not None
                else None
            ),
            feedback_comment=data.get("feedback_comment"),
            feedback_timestamp_items=list(
                data.get("feedback_timestamp_items") or []
            ),
            feedback_tags=list(data.get("feedback_tags") or []),
            feedback_submitted_by=data.get("feedback_submitted_by"),
            feedback_submitted_at=data.get("feedback_submitted_at"),

            output_preset_requested=data.get("output_preset_requested"),
            output_platform_requested=data.get("output_platform_requested"),
            output_resolution_requested=data.get("output_resolution_requested"),
            output_fps_requested=data.get("output_fps_requested"),
            output_codec_preference=data.get("output_codec_preference"),
            output_audio_lufs_requested=data.get("output_audio_lufs_requested"),
            output_container_requested=data.get("output_container_requested"),

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
