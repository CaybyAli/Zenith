"""Gaming Pipeline - core/gaming_pipeline.py

Isoliertes Pipeline-Modul fÃ¼r gaming_main und gaming_uncut.
Output: <export_dir>/<job_id>/<job_id>_final.mp4

Entfernt gegenÃ¼ber app.py (werden in spÃ¤teren Phasen separat gebaut):
  - Music: MusicCueEngine, AudioMixPlanner, MusicApplyProcessor, etc.
  - Thumbnails: ThumbnailForge, AIThumbnailForge
  - Shorts: ShortsDecisionEngine, ShortsGenerator
  - Publishing: PublishPackageBuilder, AutopublishGate, Publisher
  - ContentVariantBuilder / ContentVariantRepository
"""

from __future__ import annotations

import json
import logging
import os

from shared.enums import ChannelType, JobStatus, TargetFormat

from core.gaming_analyzer import GamingAnalyzer
from core.gaming_cutter import GamingCutter
from core.render_processor import RenderProcessor
from core.subtitle_processor import SubtitleProcessor
from core.title_generator import TitleGenerator
from core.metadata_generator import MetadataGenerator
from core.validator import Validator
from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError
from core.hook_keyword_extractor import HookKeywordExtractor
from core.sentence_timeline_builder import SentenceTimelineBuilder

from core.edit_signal_extractor import EditSignalExtractor
from core.cut_indicator_builder import CutIndicatorBuilder
from core.audio_role_indicator_builder import AudioRoleIndicatorBuilder
from core.gameplay_event_indicator_builder import GameplayEventIndicatorBuilder
from core.gameplay_state_analyzer import GameplayStateAnalyzer
from core.editing_profile_registry import resolve
from core.universal_moment_brain import UniversalMomentBrain
from core.universal_moment_debug_reporter import UniversalMomentDebugReporter
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from core.universal_context_auditor import UniversalContextAuditor
from core.universal_boundary_evidence_reporter import UniversalBoundaryEvidenceReporter
from core.universal_role_decision_auditor import UniversalRoleDecisionAuditor
from core.universal_moment_soft_decision_builder import UniversalMomentSoftDecisionBuilder
from core.phase_2b_final_review_builder import Phase2BFinalReviewBuilder
from core.phase_2b_stabilization_checker import Phase2BStabilizationChecker
from core.facecam_emotion_indicator_builder import FacecamEmotionIndicatorBuilder
from core.energy_curve_builder import EnergyCurveBuilder
from core.gameplay_vision_analyzer import GameplayVisionAnalyzer
from core.facecam_reaction_analyzer import FacecamReactionAnalyzer
from core.round_phase_detector import RoundPhaseDetector
from core.highlight_selector import HighlightSelector
from core.facecam_intro_guard import FacecamIntroGuard
from core.longform_timeline_builder import LongformTimelineBuilder
from core.universal_safe_edge_trim_applier import UniversalSafeEdgeTrimApplier
from core.reframing_core import ReframingCore
from core.reaction_moment_detector import ReactionMomentDetector
from core.zoom_pacing_engine import ZoomPacingEngine
from core.facecam_zoom_smoothness_guard import FacecamZoomSmoothnessGuard
from core.final_render_driver import FinalRenderDriver
from core.ffmpeg_helper import ensure_ffmpeg_on_path
from core.debug_mode import build_debug_context
from core.channel_cut_profile_provider import ChannelCutProfileProvider
from core.profile_manager import ProfileManager
from core.job_profile_metadata import apply_profile_metadata_to_job
from core.file_handler import run_file_handler_for_job
from core.preprocessing_pipeline import run_preprocessing_pipeline_for_job
from core.rms_energy_runner import run_rms_energy_for_job
from core.rms_energy_context_adapter import adapt_rms_energy_run_report_to_context
from core.energy_peak_runner import run_energy_peak_detection_for_job
from core.silence_detection_runner import run_silence_detection_for_job
from core.silence_classifier_runner import run_silence_classifier_for_job
from core.filler_word_runner import run_filler_word_detection_for_job
from core.transcript_runner import apply_transcript_run_report_to_job, run_transcript_for_job
from core.sentence_boundary_runner import (
    apply_sentence_boundary_run_report_to_job,
    run_sentence_boundary_for_job,
)
from core.keyword_emotion_runner import (
    apply_keyword_emotion_run_report_to_job,
    run_keyword_emotion_for_job,
)
from core.interaction_classification_runner import (
    apply_interaction_classification_run_report_to_job,
    run_interaction_classification_for_job,
)
from core.dead_content_runner import (
    apply_dead_content_run_report_to_job,
    run_dead_content_detection_for_job,
)
from core.content_value_runner import (
    apply_content_value_run_report_to_job,
    run_content_value_for_job,
)
from core.profanity_censor_runner import (
    apply_profanity_censor_run_report_to_job,
    run_profanity_censor_for_job,
)
from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from core.segment_classification_runner import (
    apply_segment_classification_run_report_to_job,
    run_segment_classification_for_job,
)
from core.murch_scoring_runner import (
    apply_murch_scoring_run_report_to_job,
    run_murch_scoring_for_job,
)
from core.cut_list_runner import (
    apply_cut_list_run_report_to_job,
    run_cut_list_generation_for_job,
)
from core.clip_duration_runner import (
    apply_clip_duration_run_report_to_job,
    run_clip_duration_optimization_for_job,
)
from core.transition_decision_runner import (
    apply_transition_decision_run_report_to_job,
    run_transition_decision_for_job,
)
from core.continuity_check_runner import (
    apply_continuity_check_run_report_to_job,
    run_continuity_check_for_job,
)
from core.audio_normalization_runner import run_audio_normalization_for_job
from core.beat_detection_runner import run_beat_detection_for_job
from core.scene_change_runner import (
    apply_scene_change_run_report_to_job,
    run_scene_change_for_job,
)
from core.motion_analysis_runner import (
    apply_motion_analysis_run_report_to_job,
    run_motion_analysis_for_job,
)
from core.face_reaction_runner import (
    apply_face_reaction_run_report_to_job,
    run_face_reaction_for_job,
)
from core.stutter_detection_runner import (
    apply_stutter_detection_run_report_to_job,
    run_stutter_detection_for_job,
)
from core.screen_content_runner import (
    apply_screen_content_run_report_to_job,
    run_screen_content_classification_for_job,
)
from core.visual_energy_runner import (
    apply_visual_energy_run_report_to_job,
    run_visual_energy_for_job,
)
from core.job_state_transitions import transition_job_state
from core.job_state_persistence import persist_job_state_checkpoint
from core.decision_logger import log_decision

from core.highlight_candidate_repository import HighlightCandidateRepository
from core.edit_timeline_repository import EditTimelineRepository
from core.dynamic_edit_plan_repository import DynamicEditPlanRepository
from core.reframe_plan_repository import ReframePlanRepository
from core.job_repository import JobRepository
from core.job_loader import JobLoader
from core.job_store import JobStore
from models.round_phase_result import RoundPhase, RoundPhaseResult


logger = logging.getLogger(__name__)


def _safe_log_decision(
    job,
    export_dir,
    phase: str,
    event_type: str,
    action: str,
    module: str = "gaming_pipeline",
    status: str = "ok",
    reason: str | None = None,
    score: float | None = None,
    details: dict | None = None,
):
    try:
        return log_decision(
            job=job,
            export_dir=export_dir,
            phase=phase,
            module=module,
            event_type=event_type,
            action=action,
            status=status,
            reason=reason,
            score=score,
            details=details,
        )
    except Exception as exc:
        print(
            f"[gaming_pipeline] DECISION_LOG_WARN "
            f"job={getattr(job, 'job_id', '-')} error={exc}"
        )
        return None

def _audio_normalization_event_type_for_status(status: str | None) -> str:
    status_text = str(status or "").strip().lower()

    if status_text == "ok":
        return "AUDIO_NORMALIZATION_DONE"

    if status_text == "completed_with_warnings":
        return "AUDIO_NORMALIZATION_COMPLETED_WITH_WARNINGS"

    if status_text == "blocked_missing_preprocessed_audio":
        return "AUDIO_NORMALIZATION_BLOCKED"

    if status_text in {"skipped_unsupported_source", "skipped_no_audio_source"}:
        return "AUDIO_NORMALIZATION_SKIPPED"

    if status_text == "failed":
        return "AUDIO_NORMALIZATION_FAILED"

    return "AUDIO_NORMALIZATION_FAILED"


def _apply_audio_normalization_report_to_job(job, audio_normalization_report) -> None:
    report_dict = {}

    to_dict = getattr(audio_normalization_report, "to_dict", None)
    if callable(to_dict):
        try:
            maybe_dict = to_dict()
            if isinstance(maybe_dict, dict):
                report_dict = dict(maybe_dict)
        except Exception:
            report_dict = {}

    job.audio_normalization_report = report_dict
    job.audio_normalization_status = getattr(audio_normalization_report, "status", None)
    job.audio_normalization_selected_path = getattr(audio_normalization_report, "selected_path", None)
    job.audio_normalization_selected_type = getattr(audio_normalization_report, "selected_type", None)
    job.audio_normalization_source_selection = dict(
        getattr(audio_normalization_report, "source_selection", {}) or {}
    )
    job.audio_normalization_result = dict(
        getattr(audio_normalization_report, "normalization_result", {}) or {}
    )
    job.audio_normalization_level_status = getattr(audio_normalization_report, "level_status", None)
    job.audio_normalization_needed = bool(
        getattr(audio_normalization_report, "normalization_needed", False)
    )
    job.audio_normalization_recommendation = getattr(audio_normalization_report, "recommendation", None)

    job.audio_normalization_target_rms_dbfs = float(
        getattr(audio_normalization_report, "target_rms_dbfs", -18.0) or -18.0
    )
    job.audio_normalization_target_peak_dbfs = float(
        getattr(audio_normalization_report, "target_peak_dbfs", -1.0) or -1.0
    )
    job.audio_normalization_recommended_gain_db = float(
        getattr(audio_normalization_report, "recommended_gain_db", 0.0) or 0.0
    )
    job.audio_normalization_limited_gain_db = float(
        getattr(audio_normalization_report, "limited_gain_db", 0.0) or 0.0
    )
    job.audio_normalization_gain_limited_by_peak = bool(
        getattr(audio_normalization_report, "gain_limited_by_peak", False)
    )
    job.audio_normalization_would_clip_after_gain = bool(
        getattr(audio_normalization_report, "would_clip_after_gain", False)
    )

    job.audio_normalization_peak_dbfs = getattr(audio_normalization_report, "peak_dbfs", None)
    job.audio_normalization_rms_dbfs = getattr(audio_normalization_report, "rms_dbfs", None)
    job.audio_normalization_peak_amplitude = float(
        getattr(audio_normalization_report, "peak_amplitude", 0.0) or 0.0
    )
    job.audio_normalization_rms = float(
        getattr(audio_normalization_report, "rms", 0.0) or 0.0
    )
    job.audio_normalization_clipping_sample_count = int(
        getattr(audio_normalization_report, "clipping_sample_count", 0) or 0
    )
    job.audio_normalization_clipping_ratio = float(
        getattr(audio_normalization_report, "clipping_ratio", 0.0) or 0.0
    )
    job.audio_normalization_sample_count = int(
        getattr(audio_normalization_report, "sample_count", 0) or 0
    )
    job.audio_normalization_duration_seconds = float(
        getattr(audio_normalization_report, "duration_seconds", 0.0) or 0.0
    )
    job.audio_normalization_sample_rate = getattr(audio_normalization_report, "sample_rate", None)
    job.audio_normalization_channels = getattr(audio_normalization_report, "channels", None)


def _audio_normalization_decision_details(audio_normalization_report) -> dict:
    return {
        "status": getattr(audio_normalization_report, "status", None),
        "selected_type": getattr(audio_normalization_report, "selected_type", None),
        "selected_path": getattr(audio_normalization_report, "selected_path", None),
        "level_status": getattr(audio_normalization_report, "level_status", None),
        "normalization_needed": bool(
            getattr(audio_normalization_report, "normalization_needed", False)
        ),
        "recommended_gain_db": getattr(audio_normalization_report, "recommended_gain_db", 0.0),
        "limited_gain_db": getattr(audio_normalization_report, "limited_gain_db", 0.0),
        "gain_limited_by_peak": bool(
            getattr(audio_normalization_report, "gain_limited_by_peak", False)
        ),
        "would_clip_after_gain": bool(
            getattr(audio_normalization_report, "would_clip_after_gain", False)
        ),
        "peak_dbfs": getattr(audio_normalization_report, "peak_dbfs", None),
        "rms_dbfs": getattr(audio_normalization_report, "rms_dbfs", None),
        "clipping_sample_count": int(
            getattr(audio_normalization_report, "clipping_sample_count", 0) or 0
        ),
        "recommendation": getattr(audio_normalization_report, "recommendation", None),
        "warnings": list(getattr(audio_normalization_report, "warnings", []) or []),
        "errors": list(getattr(audio_normalization_report, "errors", []) or []),
    }


def _beat_detection_event_type_for_status(status: str | None) -> str:
    status_text = str(status or "").strip().lower()

    if status_text == "ok":
        return "BEAT_DETECTION_DONE"

    if status_text == "completed_with_warnings":
        return "BEAT_DETECTION_COMPLETED_WITH_WARNINGS"

    if status_text == "blocked_missing_preprocessed_audio":
        return "BEAT_DETECTION_BLOCKED"

    if status_text in {"skipped_unsupported_source", "skipped_no_audio_source"}:
        return "BEAT_DETECTION_SKIPPED"

    if status_text == "failed":
        return "BEAT_DETECTION_FAILED"

    return "BEAT_DETECTION_FAILED"


def _apply_beat_detection_report_to_job(job, beat_detection_report) -> None:
    report_dict = {}

    to_dict = getattr(beat_detection_report, "to_dict", None)
    if callable(to_dict):
        try:
            maybe_dict = to_dict()
            if isinstance(maybe_dict, dict):
                report_dict = dict(maybe_dict)
        except Exception:
            report_dict = {}

    job.beat_detection_report = report_dict
    job.beat_detection_status = getattr(beat_detection_report, "status", None)
    job.beat_detection_selected_path = getattr(beat_detection_report, "selected_path", None)
    job.beat_detection_selected_type = getattr(beat_detection_report, "selected_type", None)
    job.beat_detection_source_selection = dict(
        getattr(beat_detection_report, "source_selection", {}) or {}
    )
    job.beat_detection_result = dict(
        getattr(beat_detection_report, "beat_detection_result", {}) or {}
    )
    job.beat_detection_beats = list(getattr(beat_detection_report, "beats", []) or [])
    job.beat_detection_beat_count = int(
        getattr(beat_detection_report, "beat_count", 0) or 0
    )
    job.beat_detection_estimated_bpm = getattr(
        beat_detection_report, "estimated_bpm", None
    )
    job.beat_detection_average_beat_interval_seconds = getattr(
        beat_detection_report, "average_beat_interval_seconds", None
    )
    job.beat_detection_duration_seconds = float(
        getattr(beat_detection_report, "duration_seconds", 0.0) or 0.0
    )
    job.beat_detection_sample_rate = getattr(beat_detection_report, "sample_rate", None)
    job.beat_detection_channels = getattr(beat_detection_report, "channels", None)
    job.beat_detection_energy_frame_count = int(
        getattr(beat_detection_report, "energy_frame_count", 0) or 0
    )
    job.beat_detection_peak_threshold = float(
        getattr(beat_detection_report, "peak_threshold", 1.35) or 1.35
    )
    job.beat_detection_min_beat_distance_seconds = float(
        getattr(beat_detection_report, "min_beat_distance_seconds", 0.25) or 0.25
    )
    job.beat_detection_max_beat_strength = float(
        getattr(beat_detection_report, "max_beat_strength", 0.0) or 0.0
    )
    job.beat_detection_avg_beat_strength = float(
        getattr(beat_detection_report, "avg_beat_strength", 0.0) or 0.0
    )
    job.beat_detection_top_beat = dict(
        getattr(beat_detection_report, "top_beat", {}) or {}
    )
    job.beat_detection_recommendation = getattr(
        beat_detection_report, "recommendation", None
    )


def _beat_detection_decision_details(beat_detection_report) -> dict:
    return {
        "status": getattr(beat_detection_report, "status", None),
        "selected_type": getattr(beat_detection_report, "selected_type", None),
        "selected_path": getattr(beat_detection_report, "selected_path", None),
        "beat_count": int(getattr(beat_detection_report, "beat_count", 0) or 0),
        "estimated_bpm": getattr(beat_detection_report, "estimated_bpm", None),
        "average_beat_interval_seconds": getattr(
            beat_detection_report, "average_beat_interval_seconds", None
        ),
        "duration_seconds": getattr(beat_detection_report, "duration_seconds", 0.0),
        "energy_frame_count": int(
            getattr(beat_detection_report, "energy_frame_count", 0) or 0
        ),
        "max_beat_strength": getattr(beat_detection_report, "max_beat_strength", 0.0),
        "avg_beat_strength": getattr(beat_detection_report, "avg_beat_strength", 0.0),
        "recommendation": getattr(beat_detection_report, "recommendation", None),
        "warnings": list(getattr(beat_detection_report, "warnings", []) or []),
        "errors": list(getattr(beat_detection_report, "errors", []) or []),
    }

def _scene_change_event_type_for_status(status: str | None) -> str:
    status_text = str(status or "").strip().lower()

    if status_text in {"ok", "completed_with_warnings"}:
        return "SCENE_CHANGE_DONE"

    if status_text == "skipped_no_video_source":
        return "SCENE_CHANGE_SKIPPED"

    if status_text == "blocked_missing_video_source":
        return "SCENE_CHANGE_BLOCKED"

    if status_text == "failed":
        return "SCENE_CHANGE_FAILED"

    return "SCENE_CHANGE_FAILED"


def _scene_change_decision_details(scene_change_report) -> dict:
    return {
        "status": getattr(scene_change_report, "status", None),
        "selected_type": getattr(scene_change_report, "selected_type", None),
        "selected_path": getattr(scene_change_report, "selected_path", None),
        "scene_change_count": int(
            getattr(scene_change_report, "scene_change_count", 0) or 0
        ),
        "hard_change_count": int(
            getattr(scene_change_report, "hard_change_count", 0) or 0
        ),
        "soft_transition_count": int(
            getattr(scene_change_report, "soft_transition_count", 0) or 0
        ),
        "false_positive_candidate_count": int(
            getattr(scene_change_report, "false_positive_candidate_count", 0) or 0
        ),
        "threshold": getattr(scene_change_report, "threshold", None),
        "duration_seconds": getattr(scene_change_report, "duration_seconds", None),
        "recommendation": getattr(scene_change_report, "recommendation", None),
        "warnings": list(getattr(scene_change_report, "warnings", []) or []),
        "errors": list(getattr(scene_change_report, "errors", []) or []),
    }


_PHASE_FILTER_BLOCKED = {RoundPhase.MENU_WAIT, RoundPhase.QUEUE_WAIT}
_PHASE_FILTER_OVERRIDE_TYPES = {
    "hook_sentence",
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
    "goal_or_save_like_flash",
    "high_action_burst",
    "sustained_action",
}
_PHASE_FILTER_IMPORTANT_WORDS = {
    "alles gut",
    "oh gott",
    "nein",
    "warte",
    "wichtig",
    "krass",
    "tor",
    "rein",
}


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _compact_log_value(value: object, fallback: str = "none", limit: int = 260) -> str:
    text = " ".join(str(value or fallback).split())
    return (text[:limit] if text else fallback)


def _job_input_path(job):
    for attr in ["raw_video_path", "input_file", "source_file", "video_path", "file_path"]:
        value = getattr(job, attr, None)
        if value:
            return value
    return None


def _load_json_profile_for_job(job) -> dict:
    channel_type = getattr(job, "channel_type", None)
    profile_id = getattr(channel_type, "value", channel_type) or "gaming_main"
    profile_id = str(profile_id)

    profile = ProfileManager().load_profile(profile_id)

    source = (
        f"profiles/{profile_id}.json"
        if not profile.get("_is_fallback")
        else "fallback"
    )

    log_line = (
        f"[gaming_pipeline] JSON_PROFILE job={job.job_id} "
        f"profile={profile.get('profile_id')} "
        f"quality_mode={profile.get('quality_mode')} "
        f"cut_aggressiveness={profile.get('cut_aggressiveness')} "
        f"source={source}"
    )
    logger.info(log_line)
    print(log_line)

    return profile


def _write_profile_snapshot(job, profile: dict) -> str:
    channel_type = getattr(job, "channel_type", None)
    channel_value = getattr(channel_type, "value", channel_type) or "gaming_main"
    channel_value = str(channel_value)

    export_dir = os.path.join("exports", channel_value, job.job_id)
    os.makedirs(export_dir, exist_ok=True)

    snapshot = {
        "job_id": job.job_id,
        "profile_id": profile.get("profile_id"),
        "channel_type": profile.get("channel_type", channel_value),
        "quality_mode": profile.get("quality_mode"),
        "cut_aggressiveness": profile.get("cut_aggressiveness"),
        "source_aspect_ratio": profile.get("source_aspect_ratio"),
        "target_format": profile.get("target_format"),
        "reframing_mode": profile.get("reframing_mode"),
        "music_enabled": profile.get("music_enabled"),
        "camera_zoom_enabled": profile.get("camera_zoom_enabled"),
        "gameplay_zoom_enabled": profile.get("gameplay_zoom_enabled"),
        "profile_version": profile.get("version"),
    }

    snapshot_path = os.path.join(export_dir, "profile_snapshot.json")

    with open(snapshot_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)

    print(
        f"[gaming_pipeline] PROFILE_SNAPSHOT job={job.job_id} "
        f"path={snapshot_path}"
    )

    return snapshot_path

def _write_universal_debug_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_universal_moment_debug.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "universal_moment_debug.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_universal_soft_decision_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_universal_moment_soft_decision.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "universal_moment_soft_decision.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_universal_role_decision_audit_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_universal_role_decision_audit.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "universal_role_decision_audit.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_universal_context_audit_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_universal_context_audit.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "universal_context_audit.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_universal_boundary_evidence_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_universal_boundary_evidence.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "universal_boundary_evidence.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_phase_2b_final_review_report(job, report) -> list[str]:
    if report is None:
        return []

    payload = report.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_phase_2b_final_review.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "phase_2b_final_review.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_phase_2b_stabilization_result(job, result) -> list[str]:
    if result is None:
        return []

    payload = result.to_dict()
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{job.job_id}_phase_2b_stabilization_result.json")

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "phase_2b_stabilization_result.json")

    paths = [output_path, export_path]
    for path in paths:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return paths


def _write_phase_2b_stabilization_review(job, result) -> list[str]:
    if result is None:
        return []

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)

    checker = Phase2BStabilizationChecker()
    output_path = checker.write_markdown(
        result=result,
        output_dir=output_dir,
        filename=f"{job.job_id}_phase_2b_stabilization_review.md",
    )
    export_path = checker.write_markdown(
        result=result,
        output_dir=export_dir,
        filename="phase_2b_stabilization_review.md",
    )
    return [str(output_path), str(export_path)]


def _write_universal_review_report(
    job,
    report,
    soft_decision_report=None,
    role_decision_audit_report=None,
    context_audit_report=None,
    boundary_evidence_report=None,
    final_review_report=None,
) -> list[str]:
    if report is None:
        return []

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    os.makedirs(export_dir, exist_ok=True)

    exporter = UniversalMomentReviewExporter()
    output_path = exporter.write_report(
        report=report,
        output_dir=output_dir,
        filename=f"{job.job_id}_universal_moment_review.md",
        soft_decision_report=soft_decision_report,
        role_decision_audit_report=role_decision_audit_report,
        context_audit_report=context_audit_report,
        boundary_evidence_report=boundary_evidence_report,
        final_review_report=final_review_report,
    )
    export_path = exporter.write_report(
        report=report,
        output_dir=export_dir,
        filename="universal_moment_review.md",
        soft_decision_report=soft_decision_report,
        role_decision_audit_report=role_decision_audit_report,
        context_audit_report=context_audit_report,
        boundary_evidence_report=boundary_evidence_report,
        final_review_report=final_review_report,
    )
    return [str(output_path), str(export_path)]


def _transcript_text_for_window(transcript_result, start: float, end: float) -> str:
    if transcript_result is None:
        return ""
    return " ".join(
        segment.text.lower()
        for segment in transcript_result.segments
        if _overlap_seconds(start, end, segment.start_seconds, segment.end_seconds) > 0.0
    )


def _has_phase_override(candidate, cut_indicator_result, transcript_result) -> bool:
    start = max(0.0, candidate.start_time - 0.5)
    end = candidate.end_time + 0.5
    for indicator in getattr(cut_indicator_result, "indicators", []) or []:
        if _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) <= 0.0:
            continue
        if indicator.indicator_type in _PHASE_FILTER_OVERRIDE_TYPES and indicator.score >= 0.65:
            return True
        if indicator.indicator_type == "audio_peak" and indicator.score >= 0.85:
            return True
    text = _transcript_text_for_window(transcript_result, start, end)
    return any(word in text for word in _PHASE_FILTER_IMPORTANT_WORDS)


def _filter_highlights_by_round_phase(
    highlight_candidates,
    round_phase_result: RoundPhaseResult | None,
    cut_indicator_result,
    transcript_result,
) -> tuple[list, dict[str, int]]:
    stats = {"dropped": 0, "kept_override": 0}
    if round_phase_result is None or not round_phase_result.windows:
        return list(highlight_candidates), stats

    kept = []
    for candidate in highlight_candidates:
        center = round((candidate.start_time + candidate.end_time) / 2.0, 3)
        phase_window = round_phase_result.phase_at(center)
        blocked = (
            phase_window is not None
            and phase_window.phase in _PHASE_FILTER_BLOCKED
            and phase_window.confidence >= 0.5
        )
        if not blocked:
            kept.append(candidate)
            continue
        if _has_phase_override(candidate, cut_indicator_result, transcript_result):
            candidate.notes.append(f"phase_filter_override={phase_window.phase.value}")
            kept.append(candidate)
            stats["kept_override"] += 1
            continue
        candidate.notes.append(f"phase_filter_dropped={phase_window.phase.value}")
        stats["dropped"] += 1

    return kept, stats


def _build_gaming_services() -> dict:
    """Dependency-Container fÃ¼r die Gaming-Pipeline.

    Gibt ein Dict mit allen benÃ¶tigten Service-Instanzen zurÃ¼ck.
    Wird einmal in pipeline_runner.py aufgerufen und an
    run_gaming_pipeline_for_job() weitergegeben.
    """
    return {
        "analyzer":          GamingAnalyzer(),
        "cutter":            GamingCutter(),
        "renderer":          RenderProcessor(),
        "subtitle_processor": SubtitleProcessor(),
        "title_gen":         TitleGenerator(),
        "metadata_gen":      MetadataGenerator(),
        "validator":         Validator(),
        "job_repo":          JobRepository(),
        "job_loader":        JobLoader(),
        "transcript_processor": TranscriptProcessor(),
        "hook_keyword_extractor": HookKeywordExtractor(),
        "gameplay_vision_analyzer": GameplayVisionAnalyzer(),
        "facecam_reaction_analyzer": FacecamReactionAnalyzer(),
    }


def run_gaming_pipeline_for_job(job, services: dict) -> dict:
    """FÃ¼hrt die vollstÃ¤ndige Gaming-Render-Pipeline fÃ¼r einen Job aus.

    Pipeline-Schritte:
      1) GamingAnalyzer + GamingCutter  â†’ analysis + edit_decision
      2) EditSignalExtractor            â†’ edit_signals
      3) HighlightSelector              â†’ highlights
      4) LongformTimelineBuilder        â†’ edit_timeline  (wenn longform)
      5) ReframingCore                  â†’ reframe_plan
      6) ReactionMomentDetector
         + ZoomPacingEngine             â†’ dynamic_edit_plan
      7) FinalRenderDriver / RenderProcessor â†’ final_video_path
      8) SubtitleProcessor              â†’ subtitles
      9) TitleGenerator + MetadataGenerator â†’ title + metadata
     10) Validator                      â†’ validator_result
     11) Repositories speichern        (highlight, timeline, reframe, zoom)
     12) Job-Status -> JobStatus.RENDERED

    Args:
        job:      Job-Objekt (bereits geroutet)
        services: Dict aus _build_gaming_services()

    Returns:
        Dict mit allen Zwischen- und Endergebnissen.
    """

    analyzer          = services["analyzer"]
    cutter            = services["cutter"]
    renderer          = services["renderer"]
    subtitle_processor = services["subtitle_processor"]
    title_gen         = services["title_gen"]
    metadata_gen      = services["metadata_gen"]
    validator         = services["validator"]
    job_repo          = services["job_repo"]
    transcript_processor = services.get("transcript_processor") or TranscriptProcessor()

    universal_moment_debug_report = None
    universal_moment_soft_decision_report = None
    universal_role_decision_audit_report = None
    universal_context_audit_report = None
    universal_boundary_evidence_report = None
    phase_2b_final_review_report = None
    phase_2b_stabilization_result = None
    universal_moment_debug_paths: list[str] = []
    universal_moment_soft_decision_paths: list[str] = []
    universal_role_decision_audit_paths: list[str] = []
    universal_context_audit_paths: list[str] = []
    universal_boundary_evidence_paths: list[str] = []
    phase_2b_final_review_paths: list[str] = []
    universal_moment_review_paths: list[str] = []
    phase_2b_stabilization_paths: list[str] = []
    phase_2b_stabilization_review_paths: list[str] = []

    json_profile = _load_json_profile_for_job(job)
    profile_snapshot_path = _write_profile_snapshot(job, json_profile)
    profile_metadata = apply_profile_metadata_to_job(
        job=job,
        profile=json_profile,
        profile_snapshot_path=profile_snapshot_path,
    )

    debug_context = build_debug_context(
        job=job,
        profile=json_profile,
        services=services,
    )
    job.debug_mode = debug_context.get("debug_mode", "off")
    job.debug_context = debug_context

    job_state_store = services.get("job_store")
    job_state_channel = getattr(
        getattr(job, "channel_type", None),
        "value",
        "gaming_main",
    )
    job_state_export_dir = os.path.join("exports", str(job_state_channel), job.job_id)

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="profile",
        event_type="PROFILE_LOADED",
        action="load_json_profile",
        reason="profile_manager_loaded_profile",
        details={
            "profile_id": json_profile.get("profile_id"),
            "quality_mode": json_profile.get("quality_mode"),
            "profile_snapshot_path": str(profile_snapshot_path),
            "profile_metadata": profile_metadata,
            "debug_context": debug_context,
        },
    )

    input_path = _job_input_path(job)
    file_handler_report = None

    if not input_path:
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="FILE_HANDLER_SKIPPED",
            action="skip_file_handler",
            status="warning",
            reason="input_path_missing",
            details={"job_id": getattr(job, "job_id", None)},
        )
    else:
        file_handler_report = run_file_handler_for_job(
            job=job,
            input_path=input_path,
            profile=json_profile,
            readability_seconds=3.0,
        )

        file_info = file_handler_report.get("file_info", {}) or {}
        file_acceptance = file_handler_report.get("file_acceptance", {}) or {}
        stream_classification = file_handler_report.get("stream_classification", {}) or {}
        file_readability = file_handler_report.get("file_readability", {}) or {}

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="FILE_PROBED",
            action="probe_input_file",
            reason="file_probe_completed",
            details={
                "input_path": str(input_path),
                "probe_status": file_info.get("probe_status"),
                "duration_seconds": file_info.get("duration_seconds"),
                "width": file_info.get("width"),
                "height": file_info.get("height"),
                "fps": file_info.get("fps"),
                "audio_stream_count": file_info.get("audio_stream_count"),
                "video_stream_count": file_info.get("video_stream_count"),
            },
        )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="FILE_ACCEPTANCE_CHECKED",
            action="validate_input_file",
            status=file_acceptance.get("severity", "ok"),
            reason=file_acceptance.get("recommendation"),
            details={
                "accepted": file_acceptance.get("accepted"),
                "status": file_acceptance.get("status"),
                "warnings": file_acceptance.get("warnings", []),
                "errors": file_acceptance.get("errors", []),
                "recommendation": file_acceptance.get("recommendation"),
            },
        )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="STREAMS_CLASSIFIED",
            action="classify_streams",
            status="warning" if stream_classification.get("needs_manual_review") else "ok",
            reason="manual_review_needed" if stream_classification.get("needs_manual_review") else "streams_classified",
            details={
                "stream_count": stream_classification.get("stream_count"),
                "needs_manual_review": stream_classification.get("needs_manual_review"),
                "primary_video_stream": stream_classification.get("primary_video_stream"),
                "voice_audio_candidate_count": len(stream_classification.get("voice_audio_candidates", []) or []),
                "game_audio_candidate_count": len(stream_classification.get("game_audio_candidates", []) or []),
                "unknown_audio_stream_count": len(stream_classification.get("unknown_audio_streams", []) or []),
                "warnings": stream_classification.get("warnings", []),
            },
        )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="FILE_READABILITY_CHECKED",
            action="check_file_readability",
            status=file_readability.get("severity", "error") if file_readability else "skipped",
            reason=file_readability.get("recommendation", "skipped") if file_readability else "acceptance_rejected_before_readability",
            details={
                "readable": file_readability.get("readable") if file_readability else False,
                "status": file_readability.get("status") if file_readability else "skipped",
                "warnings": file_readability.get("warnings", []) if file_readability else [],
                "errors": file_readability.get("errors", []) if file_readability else [],
                "recommendation": file_readability.get("recommendation") if file_readability else "reject",
            },
        )

        persist_job_state_checkpoint(
            job=job,
            job_store=job_state_store,
            export_dir=job_state_export_dir,
            step_name="file_handler_checked",
            reason="file_handler_completed",
        )

        if not file_handler_report.get("accepted", False):
            transition_job_state(
                job,
                JobStatus.FAILED,
                module="gaming_pipeline",
                reason="file_handler_rejected_file",
            )
            persist_job_state_checkpoint(
                job=job,
                job_store=job_state_store,
                export_dir=job_state_export_dir,
                step_name="failed_file_rejected",
                reason="file_handler_rejected_file",
            )
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="file_handler",
                event_type="FILE_REJECTED",
                action="abort_pipeline",
                status="error",
                reason="file_acceptance_failed",
                details={
                    "errors": file_handler_report.get("errors", []),
                    "warnings": file_handler_report.get("warnings", []),
                    "recommendation": file_handler_report.get("recommendation"),
                },
            )
            raise RuntimeError(
                f"File rejected by file handler: {file_handler_report.get('errors', [])}"
            )

        if not file_handler_report.get("readable", False):
            transition_job_state(
                job,
                JobStatus.FAILED,
                module="gaming_pipeline",
                reason="file_handler_unreadable_file",
            )
            persist_job_state_checkpoint(
                job=job,
                job_store=job_state_store,
                export_dir=job_state_export_dir,
                step_name="failed_file_unreadable",
                reason="file_handler_unreadable_file",
            )
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="file_handler",
                event_type="FILE_UNREADABLE",
                action="abort_pipeline",
                status="error",
                reason="file_readability_failed",
                details={
                    "errors": file_handler_report.get("errors", []),
                    "warnings": file_handler_report.get("warnings", []),
                    "recommendation": file_handler_report.get("recommendation"),
                },
            )
            raise RuntimeError(
                f"File unreadable by file handler: {file_handler_report.get('errors', [])}"
            )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="file_handler",
            event_type="FILE_HANDLER_PASSED",
            action="continue_pipeline",
            reason="file_handler_passed",
            details={
                "accepted": file_handler_report.get("accepted"),
                "readable": file_handler_report.get("readable"),
                "status": file_handler_report.get("status"),
                "recommendation": file_handler_report.get("recommendation"),
                "needs_manual_review": file_handler_report.get("needs_manual_review"),
                "warnings": file_handler_report.get("warnings", []),
            },
        )

    if not input_path:
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="preprocessing",
            event_type="PREPROCESSING_FAILED",
            action="abort_pipeline",
            status="error",
            reason="input_path_missing",
            details={"job_id": getattr(job, "job_id", None)},
        )
        raise RuntimeError("Preprocessing failed: input_path_missing")

    preprocessing_report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=input_path,
        root_dir="preprocessed",
        metadata={
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="preprocessing",
        event_type="PREPROCESSING_WORKSPACE_READY",
        action="prepare_preprocessing_workspace",
        reason="preprocessing_workspace_ready",
        details={
            "preprocessing_dir": preprocessing_report.get("preprocessing_dir"),
            "manifest_path": preprocessing_report.get("manifest_path"),
            "status": preprocessing_report.get("status"),
            "reused_cache": preprocessing_report.get("reused_cache"),
            "cache_key": job.preprocessing_cache_key,
        },
    )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="preprocessing",
        event_type="AUDIO_EXTRACTION_PLAN_READY",
        action="build_audio_extraction_plan",
        reason="audio_extraction_plan_ready",
        details={
            "status": job.audio_extraction_plan.get("status"),
            "target_count": len(job.audio_targets),
            "target_ids": [
                target.get("target_id")
                for target in job.audio_targets
            ],
        },
    )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="preprocessing",
        event_type="FRAME_EXTRACTION_PLAN_READY",
        action="build_frame_extraction_plan",
        reason="frame_extraction_plan_ready",
        details={
            "status": job.frame_extraction_plan.get("status"),
            "target_count": len(job.frame_targets),
            "target_ids": [
                target.get("target_id")
                for target in job.frame_targets
            ],
        },
    )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="preprocessing",
        event_type="PREPROCESSING_CACHE_VALIDATED",
        action="validate_preprocessing_cache",
        status=job.preprocessing_cache_validation.get("severity", "ok"),
        reason=preprocessing_report.get("recommendation"),
        details={
            "reusable": job.preprocessing_cache_reuse_allowed,
            "status": job.preprocessing_cache_validation_status,
            "severity": job.preprocessing_cache_validation.get("severity"),
            "warnings": preprocessing_report.get("warnings", []),
            "errors": preprocessing_report.get("errors", []),
            "recommendation": preprocessing_report.get("recommendation"),
        },
    )

    if preprocessing_report.get("errors"):
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="preprocessing",
            event_type="PREPROCESSING_FAILED",
            action="abort_pipeline",
            status="error",
            reason="preprocessing_errors",
            details={
                "errors": preprocessing_report.get("errors", []),
                "warnings": preprocessing_report.get("warnings", []),
                "recommendation": preprocessing_report.get("recommendation"),
            },
        )
        raise RuntimeError(
            f"Preprocessing failed: {preprocessing_report.get('errors', [])}"
        )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="preprocessing",
        event_type="PREPROCESSING_READY",
        action="continue_pipeline",
        reason="preprocessing_ready",
        details={
            "status": preprocessing_report.get("status"),
            "cache_reuse_allowed": preprocessing_report.get("cache_reuse_allowed"),
            "warnings": preprocessing_report.get("warnings", []),
            "errors": preprocessing_report.get("errors", []),
        },
    )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="preprocessing_ready",
        reason="preprocessing_workspace_and_plans_ready",
    )

    # ── Scene Change Detection (2B-13-C) ─────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-13-C",
        event_type="SCENE_CHANGE_STARTED",
        action="run_scene_change_detection",
        module="gaming_pipeline",
        reason="scene_change_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "raw_video_path": getattr(job, "raw_video_path", None),
            "preprocessing_manifest_path": getattr(
                job,
                "preprocessing_manifest_path",
                None,
            ),
        },
    )

    scene_change_report = None

    try:
        scene_change_report = run_scene_change_for_job(
            job=job,
            metadata={
                "profile_id": getattr(job, "profile_id", None),
                "quality_mode": getattr(job, "quality_mode", None),
                "pipeline_step": "scene_change_detection",
            },
        )

        apply_scene_change_run_report_to_job(job, scene_change_report)

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-13-C",
            event_type=_scene_change_event_type_for_status(
                getattr(scene_change_report, "status", None)
            ),
            action="scene_change_detection_completed",
            module="gaming_pipeline",
            status=getattr(scene_change_report, "status", None) or "ok",
            reason="scene_change_detection_completed_or_skipped",
            details=_scene_change_decision_details(scene_change_report),
        )

    except Exception as scene_change_exc:
        job.scene_change_status = "failed"
        job.scene_change_recommendation = "scene_detection_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-13-C",
            event_type="SCENE_CHANGE_FAILED",
            action="scene_change_detection_failed",
            module="gaming_pipeline",
            status="failed",
            reason="scene_change_detection_exception",
            details={
                "error": str(scene_change_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="scene_change_done",
        reason="scene_change_detection_completed_or_skipped",
    )
    # ── End Scene Change Detection ───────────────────────────────────────────

    # ── Motion Analysis (2B-14-C) ───────────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-14-C",
        event_type="MOTION_ANALYSIS_STARTED",
        action="run_motion_analysis",
        module="gaming_pipeline",
        reason="motion_analysis_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "raw_video_path": getattr(job, "raw_video_path", None),
            "preprocessing_manifest_path": getattr(
                job,
                "preprocessing_manifest_path",
                None,
            ),
        },
    )

    motion_analysis_report = None

    try:
        motion_analysis_report = run_motion_analysis_for_job(job)

        apply_motion_analysis_run_report_to_job(job, motion_analysis_report)

        motion_analysis_status = getattr(motion_analysis_report, "status", None)

        if motion_analysis_status in {"ok", "completed_with_warnings"}:
            motion_analysis_event_type = "MOTION_ANALYSIS_DONE"
        elif motion_analysis_status == "skipped_no_video_source":
            motion_analysis_event_type = "MOTION_ANALYSIS_SKIPPED"
        elif motion_analysis_status == "blocked_missing_video_source":
            motion_analysis_event_type = "MOTION_ANALYSIS_BLOCKED"
        else:
            motion_analysis_event_type = "MOTION_ANALYSIS_FAILED"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-14-C",
            event_type=motion_analysis_event_type,
            action="motion_analysis_completed",
            module="gaming_pipeline",
            status=motion_analysis_status or "failed",
            reason="motion_analysis_completed_or_skipped",
            details={
                "status": motion_analysis_status,
                "selected_path": getattr(motion_analysis_report, "selected_path", None),
                "selected_type": getattr(motion_analysis_report, "selected_type", None),
                "point_count": getattr(motion_analysis_report, "point_count", 0),
                "segment_count": getattr(motion_analysis_report, "segment_count", 0),
                "dead_visual_candidate_count": getattr(
                    motion_analysis_report,
                    "dead_visual_candidate_count",
                    0,
                ),
                "recommendation": getattr(
                    motion_analysis_report,
                    "recommendation",
                    None,
                ),
                "warnings": list(getattr(motion_analysis_report, "warnings", []) or []),
                "errors": list(getattr(motion_analysis_report, "errors", []) or []),
            },
        )

    except Exception as motion_analysis_exc:
        job.motion_analysis_status = "failed"
        job.motion_analysis_recommendation = "motion_analysis_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-14-C",
            event_type="MOTION_ANALYSIS_FAILED",
            action="motion_analysis_failed",
            module="gaming_pipeline",
            status="failed",
            reason="motion_analysis_exception",
            details={
                "error": str(motion_analysis_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="motion_analysis_done",
        reason="motion_analysis_completed_or_skipped",
    )
    # End Motion Analysis

    # Face Reaction Analysis (2B-15-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-15-C",
        event_type="FACE_REACTION_STARTED",
        action="run_face_reaction_analysis",
        module="gaming_pipeline",
        reason="face_reaction_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "raw_video_path": getattr(job, "raw_video_path", None),
            "preprocessing_manifest_path": getattr(
                job,
                "preprocessing_manifest_path",
                None,
            ),
        },
    )

    face_reaction_report = None

    try:
        face_reaction_report = run_face_reaction_for_job(job)

        apply_face_reaction_run_report_to_job(job, face_reaction_report)

        face_reaction_status = getattr(face_reaction_report, "status", None)

        if face_reaction_status in {"ok", "completed_with_warnings"}:
            face_reaction_event_type = "FACE_REACTION_DONE"
        elif face_reaction_status == "skipped_no_video_source":
            face_reaction_event_type = "FACE_REACTION_SKIPPED"
        elif face_reaction_status == "blocked_missing_video_source":
            face_reaction_event_type = "FACE_REACTION_BLOCKED"
        else:
            face_reaction_event_type = "FACE_REACTION_FAILED"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-15-C",
            event_type=face_reaction_event_type,
            action="face_reaction_completed",
            module="gaming_pipeline",
            status=face_reaction_status or "failed",
            reason="face_reaction_completed_or_skipped",
            details={
                "status": face_reaction_status,
                "selected_path": getattr(face_reaction_report, "selected_path", None),
                "selected_type": getattr(face_reaction_report, "selected_type", None),
                "point_count": getattr(face_reaction_report, "point_count", 0),
                "segment_count": getattr(face_reaction_report, "segment_count", 0),
                "face_detected_point_count": getattr(
                    face_reaction_report,
                    "face_detected_point_count",
                    0,
                ),
                "reaction_candidate_count": getattr(
                    face_reaction_report,
                    "reaction_candidate_count",
                    0,
                ),
                "high_reaction_segment_count": getattr(
                    face_reaction_report,
                    "high_reaction_segment_count",
                    0,
                ),
                "recommendation": getattr(
                    face_reaction_report,
                    "recommendation",
                    None,
                ),
                "warnings": list(getattr(face_reaction_report, "warnings", []) or []),
                "errors": list(getattr(face_reaction_report, "errors", []) or []),
            },
        )

    except Exception as face_reaction_exc:
        job.face_reaction_status = "failed"
        job.face_reaction_recommendation = "face_reaction_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-15-C",
            event_type="FACE_REACTION_FAILED",
            action="face_reaction_failed",
            module="gaming_pipeline",
            status="failed",
            reason="face_reaction_exception",
            details={
                "error": str(face_reaction_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="face_reaction_done",
        reason="face_reaction_completed_or_skipped",
    )
    # End Face Reaction Analysis

    # Stutter Detection (2B-16-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-16-C",
        event_type="STUTTER_DETECTION_STARTED",
        action="run_stutter_detection",
        module="gaming_pipeline",
        reason="stutter_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "raw_video_path": getattr(job, "raw_video_path", None),
            "preprocessing_manifest_path": getattr(
                job,
                "preprocessing_manifest_path",
                None,
            ),
        },
    )

    stutter_detection_report = None

    try:
        stutter_detection_report = run_stutter_detection_for_job(job)

        apply_stutter_detection_run_report_to_job(job, stutter_detection_report)

        stutter_detection_status = getattr(stutter_detection_report, "status", None)

        if stutter_detection_status in {"ok", "completed_with_warnings"}:
            stutter_detection_event_type = "STUTTER_DETECTION_DONE"
        elif stutter_detection_status == "skipped_no_video_source":
            stutter_detection_event_type = "STUTTER_DETECTION_SKIPPED"
        elif stutter_detection_status == "blocked_missing_video_source":
            stutter_detection_event_type = "STUTTER_DETECTION_BLOCKED"
        else:
            stutter_detection_event_type = "STUTTER_DETECTION_FAILED"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-16-C",
            event_type=stutter_detection_event_type,
            action="stutter_detection_completed",
            module="gaming_pipeline",
            status=stutter_detection_status or "failed",
            reason="stutter_detection_completed_or_skipped",
            details={
                "status": stutter_detection_status,
                "selected_path": getattr(stutter_detection_report, "selected_path", None),
                "selected_type": getattr(stutter_detection_report, "selected_type", None),
                "point_count": getattr(stutter_detection_report, "point_count", 0),
                "segment_count": getattr(stutter_detection_report, "segment_count", 0),
                "duplicate_candidate_count": getattr(
                    stutter_detection_report,
                    "duplicate_candidate_count",
                    0,
                ),
                "stutter_segment_count": getattr(
                    stutter_detection_report,
                    "stutter_segment_count",
                    0,
                ),
                "freeze_segment_count": getattr(
                    stutter_detection_report,
                    "freeze_segment_count",
                    0,
                ),
                "recommendation": getattr(
                    stutter_detection_report,
                    "recommendation",
                    None,
                ),
                "warnings": list(getattr(stutter_detection_report, "warnings", []) or []),
                "errors": list(getattr(stutter_detection_report, "errors", []) or []),
            },
        )

    except Exception as stutter_detection_exc:
        job.stutter_detection_status = "failed"
        job.stutter_detection_recommendation = "stutter_detection_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-16-C",
            event_type="STUTTER_DETECTION_FAILED",
            action="stutter_detection_failed",
            module="gaming_pipeline",
            status="failed",
            reason="stutter_detection_exception",
            details={
                "error": str(stutter_detection_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="stutter_detection_done",
        reason="stutter_detection_completed_or_skipped",
    )
    # End Stutter Detection

    # Screen Content Classification (2B-17-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-17-C",
        event_type="SCREEN_CONTENT_STARTED",
        action="run_screen_content_classification",
        module="gaming_pipeline",
        reason="screen_content_classification_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "raw_video_path": getattr(job, "raw_video_path", None),
            "preprocessing_manifest_path": getattr(
                job,
                "preprocessing_manifest_path",
                None,
            ),
        },
    )

    screen_content_report = None

    try:
        screen_content_report = run_screen_content_classification_for_job(job)

        apply_screen_content_run_report_to_job(job, screen_content_report)

        screen_content_status = getattr(screen_content_report, "status", None)

        if screen_content_status in {"ok", "completed_with_warnings"}:
            screen_content_event_type = "SCREEN_CONTENT_DONE"
        elif screen_content_status == "skipped_no_video_source":
            screen_content_event_type = "SCREEN_CONTENT_SKIPPED"
        elif screen_content_status == "blocked_missing_video_source":
            screen_content_event_type = "SCREEN_CONTENT_BLOCKED"
        else:
            screen_content_event_type = "SCREEN_CONTENT_FAILED"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-17-C",
            event_type=screen_content_event_type,
            action="screen_content_classification_completed",
            module="gaming_pipeline",
            status=screen_content_status or "failed",
            reason="screen_content_completed_or_skipped",
            details={
                "status": screen_content_status,
                "selected_path": getattr(screen_content_report, "selected_path", None),
                "selected_type": getattr(screen_content_report, "selected_type", None),
                "point_count": getattr(screen_content_report, "point_count", 0),
                "segment_count": getattr(screen_content_report, "segment_count", 0),
                "gameplay_segment_count": getattr(
                    screen_content_report,
                    "gameplay_segment_count",
                    0,
                ),
                "menu_segment_count": getattr(
                    screen_content_report,
                    "menu_segment_count",
                    0,
                ),
                "loading_segment_count": getattr(
                    screen_content_report,
                    "loading_segment_count",
                    0,
                ),
                "scoreboard_segment_count": getattr(
                    screen_content_report,
                    "scoreboard_segment_count",
                    0,
                ),
                "death_screen_segment_count": getattr(
                    screen_content_report,
                    "death_screen_segment_count",
                    0,
                ),
                "victory_screen_segment_count": getattr(
                    screen_content_report,
                    "victory_screen_segment_count",
                    0,
                ),
                "black_screen_segment_count": getattr(
                    screen_content_report,
                    "black_screen_segment_count",
                    0,
                ),
                "recommendation": getattr(
                    screen_content_report,
                    "recommendation",
                    None,
                ),
                "warnings": list(getattr(screen_content_report, "warnings", []) or []),
                "errors": list(getattr(screen_content_report, "errors", []) or []),
            },
        )

    except Exception as screen_content_exc:
        job.screen_content_status = "failed"
        job.screen_content_recommendation = "screen_content_classification_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-17-C",
            event_type="SCREEN_CONTENT_FAILED",
            action="screen_content_classification_failed",
            module="gaming_pipeline",
            status="failed",
            reason="screen_content_exception",
            details={
                "error": str(screen_content_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="screen_content_done",
        reason="screen_content_completed_or_skipped",
    )
    # End Screen Content Classification

    # ── Visual Energy Score (2B-18-C) ───────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="2B-18-C",
        event_type="VISUAL_ENERGY_STARTED",
        action="run_visual_energy",
        module="gaming_pipeline",
        reason="visual_energy_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "scene_change_status": getattr(job, "scene_change_status", None),
            "motion_analysis_status": getattr(job, "motion_analysis_status", None),
            "face_reaction_status": getattr(job, "face_reaction_status", None),
            "stutter_detection_status": getattr(job, "stutter_detection_status", None),
            "screen_content_status": getattr(job, "screen_content_status", None),
        },
    )

    visual_energy_report = None

    try:
        visual_energy_report = run_visual_energy_for_job(job)

        apply_visual_energy_run_report_to_job(job, visual_energy_report)

        visual_energy_status = getattr(visual_energy_report, "status", None)

        if visual_energy_status in {"ok", "completed_with_warnings"}:
            visual_energy_event_type = "VISUAL_ENERGY_DONE"
        elif visual_energy_status == "skipped_no_visual_sources":
            visual_energy_event_type = "VISUAL_ENERGY_SKIPPED"
        else:
            visual_energy_event_type = "VISUAL_ENERGY_FAILED"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-18-C",
            event_type=visual_energy_event_type,
            action="visual_energy_completed",
            module="gaming_pipeline",
            status=visual_energy_status or "failed",
            reason="visual_energy_completed_or_skipped",
            details={
                "status": visual_energy_status,
                "point_count": getattr(visual_energy_report, "point_count", 0),
                "segment_count": getattr(visual_energy_report, "segment_count", 0),
                "high_energy_segment_count": getattr(
                    visual_energy_report,
                    "high_energy_segment_count",
                    0,
                ),
                "low_energy_segment_count": getattr(
                    visual_energy_report,
                    "low_energy_segment_count",
                    0,
                ),
                "technical_warning_segment_count": getattr(
                    visual_energy_report,
                    "technical_warning_segment_count",
                    0,
                ),
                "duration_seconds": getattr(
                    visual_energy_report,
                    "duration_seconds",
                    None,
                ),
                "frame_sample_rate": getattr(
                    visual_energy_report,
                    "frame_sample_rate",
                    None,
                ),
                "recommendation": getattr(
                    visual_energy_report,
                    "recommendation",
                    None,
                ),
                "warnings": list(getattr(visual_energy_report, "warnings", []) or []),
                "errors": list(getattr(visual_energy_report, "errors", []) or []),
            },
        )

    except Exception as visual_energy_exc:
        job.visual_energy_status = "failed"
        job.visual_energy_recommendation = "visual_energy_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="2B-18-C",
            event_type="VISUAL_ENERGY_FAILED",
            action="visual_energy_failed",
            module="gaming_pipeline",
            status="failed",
            reason="visual_energy_exception",
            details={
                "error": str(visual_energy_exc),
                "job_id": getattr(job, "job_id", None),
            },
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="visual_energy_done",
        reason="visual_energy_completed_or_skipped",
    )
    # ── End Visual Energy Score ──────────────────────────────────────────────

    # ── RMS Energy ──────────────────────────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="rms_energy",
        event_type="RMS_ENERGY_STARTED",
        action="run_rms_energy",
        reason="rms_energy_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    try:
        rms_report = run_rms_energy_for_job(
            job=job,
            require_existing_file=True,
            allow_original_wav_fallback=True,
            frame_ms=10.0,
            hop_ms=5.0,
            silence_rms_threshold=0.001,
            metadata={
                "stage": "2B-08-E",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as rms_exc:
        rms_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="rms_energy",
            event_type="RMS_ENERGY_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="rms_energy_runner_exception",
            details={"error": str(rms_exc)},
        )

    if rms_report is not None:
        job.rms_energy_report = rms_report.to_dict()
        job.rms_energy_status = rms_report.status
        job.rms_energy_source_selection = dict(rms_report.source_selection or {})
        job.rms_energy_timeline_result = dict(rms_report.energy_timeline_result or {})
        job.rms_energy_selected_path = rms_report.selected_path
        job.rms_energy_selected_type = rms_report.selected_type
        job.rms_energy_timeline_status = rms_report.timeline_status
        job.rms_energy_point_count = int(rms_report.point_count or 0)
        job.rms_energy_duration_seconds = float(rms_report.duration_seconds or 0.0)
        job.rms_energy_sample_rate = rms_report.sample_rate
        job.rms_energy_channels = rms_report.channels
        job.rms_energy_frame_ms = float(rms_report.frame_ms or 10.0)
        job.rms_energy_hop_ms = float(rms_report.hop_ms or 5.0)
        job.rms_energy_min_rms = float(rms_report.min_rms or 0.0)
        job.rms_energy_max_rms = float(rms_report.max_rms or 0.0)
        job.rms_energy_avg_rms = float(rms_report.avg_rms or 0.0)
        job.rms_energy_min_normalized_energy = float(rms_report.min_normalized_energy or 0.0)
        job.rms_energy_max_normalized_energy = float(rms_report.max_normalized_energy or 0.0)
        job.rms_energy_avg_normalized_energy = float(rms_report.avg_normalized_energy or 0.0)

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="rms_energy",
            event_type="RMS_ENERGY_SOURCE_SELECTED",
            action="select_rms_energy_source",
            reason=rms_report.status or "rms_energy_source_selected",
            details={
                "status": rms_report.status,
                "selected_path": rms_report.selected_path,
                "selected_type": rms_report.selected_type,
                "source_selection": dict(rms_report.source_selection or {}),
                "recommendation": rms_report.recommendation,
                "warnings": list(rms_report.warnings or []),
                "errors": list(rms_report.errors or []),
            },
        )

        if rms_report.status == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_DONE",
                action="continue_pipeline",
                reason="rms_energy_completed",
                details={
                    "status": rms_report.status,
                    "timeline_status": rms_report.timeline_status,
                    "point_count": rms_report.point_count,
                    "duration_seconds": rms_report.duration_seconds,
                    "max_normalized_energy": rms_report.max_normalized_energy,
                    "recommendation": rms_report.recommendation,
                    "warnings": list(rms_report.warnings or []),
                    "errors": list(rms_report.errors or []),
                },
            )
        elif rms_report.status == "completed_with_warnings":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_COMPLETED_WITH_WARNINGS",
                action="continue_pipeline",
                status="warn",
                reason="rms_energy_completed_with_warnings",
                details={
                    "status": rms_report.status,
                    "recommendation": rms_report.recommendation,
                    "warnings": list(rms_report.warnings or []),
                    "errors": list(rms_report.errors or []),
                },
            )
        elif rms_report.status == "blocked_missing_preprocessed_audio":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_BLOCKED",
                action="continue_pipeline",
                status="warn",
                reason="rms_energy_blocked_missing_preprocessed_audio",
                details={
                    "status": rms_report.status,
                    "recommendation": rms_report.recommendation,
                    "warnings": list(rms_report.warnings or []),
                    "errors": list(rms_report.errors or []),
                },
            )
        elif rms_report.status == "skipped_unsupported_source":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason="rms_energy_skipped_unsupported_source",
                details={
                    "status": rms_report.status,
                    "recommendation": rms_report.recommendation,
                    "warnings": list(rms_report.warnings or []),
                    "errors": list(rms_report.errors or []),
                },
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=rms_report.recommendation or "rms_energy_failed",
                details={
                    "status": rms_report.status,
                    "recommendation": rms_report.recommendation,
                    "warnings": list(rms_report.warnings or []),
                    "errors": list(rms_report.errors or []),
                },
            )

        # ── RMS Context Adapter ─────────────────────────────────────────────
        if rms_report.energy_timeline_result and int(rms_report.point_count or 0) > 0:
            try:
                adapter_result = adapt_rms_energy_run_report_to_context(rms_report)
                job.rms_energy_context_adapter = adapter_result.to_dict()
                job.rms_energy_context_timeline = list(adapter_result.energy_timeline or [])
                job.rms_energy_context_status = adapter_result.status
                job.rms_energy_context_point_count = int(adapter_result.point_count or 0)
                job.rms_energy_context_peak_count = int(adapter_result.peak_count or 0)
                job.rms_energy_context_silent_count = int(adapter_result.silent_count or 0)
                _safe_log_decision(
                    job=job,
                    export_dir=job_state_export_dir,
                    phase="rms_energy",
                    event_type="RMS_ENERGY_CONTEXT_ADAPTED",
                    action="adapt_rms_energy_context",
                    reason="rms_energy_context_adapted",
                    details={
                        "status": adapter_result.status,
                        "point_count": adapter_result.point_count,
                        "peak_count": adapter_result.peak_count,
                        "silent_count": adapter_result.silent_count,
                        "warnings": list(adapter_result.warnings or []),
                        "errors": list(adapter_result.errors or []),
                    },
                )
            except Exception as adapter_exc:
                job.rms_energy_context_adapter = {}
                job.rms_energy_context_timeline = []
                job.rms_energy_context_status = "skipped_no_energy_timeline"
                job.rms_energy_context_point_count = 0
                job.rms_energy_context_peak_count = 0
                job.rms_energy_context_silent_count = 0
                _safe_log_decision(
                    job=job,
                    export_dir=job_state_export_dir,
                    phase="rms_energy",
                    event_type="RMS_ENERGY_CONTEXT_SKIPPED",
                    action="continue_pipeline",
                    status="warn",
                    reason="rms_energy_context_adapter_exception",
                    details={
                        "reason": "no_energy_timeline_available",
                        "rms_energy_status": rms_report.status,
                        "point_count": int(rms_report.point_count or 0),
                        "error": str(adapter_exc),
                    },
                )
        else:
            job.rms_energy_context_adapter = {}
            job.rms_energy_context_timeline = []
            job.rms_energy_context_status = "skipped_no_energy_timeline"
            job.rms_energy_context_point_count = 0
            job.rms_energy_context_peak_count = 0
            job.rms_energy_context_silent_count = 0
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="rms_energy",
                event_type="RMS_ENERGY_CONTEXT_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason="rms_energy_context_skipped",
                details={
                    "reason": "no_energy_timeline_available",
                    "rms_energy_status": rms_report.status,
                    "point_count": int(rms_report.point_count or 0),
                },
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="rms_energy_done",
        reason="rms_energy_completed_or_skipped",
    )
    # ── End RMS Energy ───────────────────────────────────────────────────────

    # ── Energy Peak Detection (2B-09-C) ──────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="energy_peak_detection",
        event_type="ENERGY_PEAK_DETECTION_STARTED",
        action="run_energy_peak_detection",
        reason="energy_peak_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "rms_energy_status": getattr(job, "rms_energy_status", None),
            "rms_energy_context_status": getattr(job, "rms_energy_context_status", None),
            "rms_energy_context_point_count": int(getattr(job, "rms_energy_context_point_count", 0) or 0),
        },
    )

    try:
        energy_peak_report = run_energy_peak_detection_for_job(
            job=job,
            peak_threshold=0.85,
            rise_threshold=0.25,
            min_peak_distance_seconds=0.4,
            local_window_size=1,
            max_peaks=None,
            metadata={
                "stage": "2B-09-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as energy_peak_exc:
        energy_peak_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="energy_peak_detection",
            event_type="ENERGY_PEAK_DETECTION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="energy_peak_runner_exception",
            details={"error": str(energy_peak_exc)},
        )

    if energy_peak_report is not None:
        job.energy_peak_report = energy_peak_report.to_dict()
        job.energy_peak_status = energy_peak_report.status
        job.energy_peak_timeline_source = energy_peak_report.energy_timeline_source
        job.energy_peak_detection_result = dict(energy_peak_report.peak_detection_result or {})
        job.energy_peaks = list(energy_peak_report.peaks or [])
        job.energy_peak_count = int(energy_peak_report.peak_count or 0)
        job.energy_high_energy_peak_count = int(energy_peak_report.high_energy_peak_count or 0)
        job.energy_local_max_peak_count = int(energy_peak_report.local_max_peak_count or 0)
        job.energy_rise_peak_count = int(energy_peak_report.rise_peak_count or 0)
        job.energy_threshold_peak_count = int(energy_peak_report.threshold_peak_count or 0)
        job.energy_peak_threshold = float(energy_peak_report.peak_threshold or 0.85)
        job.energy_rise_threshold = float(energy_peak_report.rise_threshold or 0.25)
        job.energy_min_peak_distance_seconds = float(energy_peak_report.min_peak_distance_seconds or 0.4)
        job.energy_max_peak_score = float(energy_peak_report.max_peak_score or 0.0)
        job.energy_avg_peak_score = float(energy_peak_report.avg_peak_score or 0.0)
        job.energy_top_peak = dict(energy_peak_report.top_peak or {})
        job.energy_peak_recommendation = energy_peak_report.recommendation

        _energy_peak_details = {
            "status": energy_peak_report.status,
            "energy_timeline_source": energy_peak_report.energy_timeline_source,
            "peak_count": energy_peak_report.peak_count,
            "high_energy_peak_count": energy_peak_report.high_energy_peak_count,
            "local_max_peak_count": energy_peak_report.local_max_peak_count,
            "rise_peak_count": energy_peak_report.rise_peak_count,
            "threshold_peak_count": energy_peak_report.threshold_peak_count,
            "max_peak_score": energy_peak_report.max_peak_score,
            "avg_peak_score": energy_peak_report.avg_peak_score,
            "recommendation": energy_peak_report.recommendation,
            "warnings": list(energy_peak_report.warnings or []),
            "errors": list(energy_peak_report.errors or []),
        }

        if energy_peak_report.status == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="energy_peak_detection",
                event_type="ENERGY_PEAK_DETECTION_DONE",
                action="continue_pipeline",
                reason="energy_peak_detection_completed",
                details=_energy_peak_details,
            )
        elif energy_peak_report.status == "completed_with_warnings":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="energy_peak_detection",
                event_type="ENERGY_PEAK_DETECTION_COMPLETED_WITH_WARNINGS",
                action="continue_pipeline",
                status="warn",
                reason="energy_peak_detection_completed_with_warnings",
                details=_energy_peak_details,
            )
        elif energy_peak_report.status == "skipped_no_energy_timeline":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="energy_peak_detection",
                event_type="ENERGY_PEAK_DETECTION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=energy_peak_report.recommendation or "energy_peak_detection_skipped",
                details=_energy_peak_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="energy_peak_detection",
                event_type="ENERGY_PEAK_DETECTION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=energy_peak_report.recommendation or "energy_peak_detection_failed",
                details=_energy_peak_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="energy_peak_detection_done",
        reason="energy_peak_detection_completed_or_skipped",
    )
    # ── End Energy Peak Detection ────────────────────────────────────────────

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="silence_detection",
        event_type="SILENCE_DETECTION_STARTED",
        action="run_silence_detection",
        reason="silence_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    try:
        silence_report = run_silence_detection_for_job(
            job=job,
            profile=json_profile,
        )
    except Exception as silence_exc:
        silence_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="silence_detection",
            event_type="SILENCE_DETECTION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="silence_detection_runner_exception",
            details={"error": str(silence_exc)},
        )

    if silence_report is not None:
        job.silence_detection_report = silence_report.to_dict()
        job.silence_detection_result = dict(silence_report.detection_result or {})
        job.silence_detection_status = silence_report.status
        job.silence_detection_source_path = silence_report.source_path
        job.silence_detection_source_type = silence_report.source_type
        job.silence_detection_threshold_db = silence_report.threshold_db
        job.silence_detection_min_duration_seconds = silence_report.min_duration_seconds
        job.silence_segment_count = int(silence_report.segment_count or 0)
        job.silence_total_seconds = float(silence_report.total_silence_seconds or 0.0)

        audio_selection = silence_report.audio_source_selection or {}
        params_dict = silence_report.parameters or {}

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="silence_detection",
            event_type="SILENCE_AUDIO_SOURCE_SELECTED",
            action="select_silence_audio_source",
            reason=audio_selection.get("status") or "silence_audio_source_selected",
            details={
                "source_path": silence_report.source_path,
                "source_type": silence_report.source_type,
                "status": audio_selection.get("status"),
                "exists": audio_selection.get("exists"),
                "warnings": list(audio_selection.get("warnings") or []),
                "errors": list(audio_selection.get("errors") or []),
            },
        )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="silence_detection",
            event_type="SILENCE_PARAMETERS_RESOLVED",
            action="resolve_silence_parameters",
            reason="silence_parameters_resolved",
            details={
                "threshold_db": silence_report.threshold_db,
                "min_duration_seconds": silence_report.min_duration_seconds,
                "require_existing_audio": silence_report.require_existing_audio,
                "resolved_from": dict(params_dict.get("resolved_from") or {}),
                "profile_id": params_dict.get("profile_id"),
                "quality_mode": params_dict.get("quality_mode"),
            },
        )

        if silence_report.status == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_detection",
                event_type="SILENCE_DETECTION_DONE",
                action="continue_pipeline",
                reason="silence_detection_completed",
                details={
                    "status": silence_report.status,
                    "segment_count": silence_report.segment_count,
                    "total_silence_seconds": silence_report.total_silence_seconds,
                    "recommendation": silence_report.recommendation,
                    "warnings": list(silence_report.warnings or []),
                    "errors": list(silence_report.errors or []),
                },
            )
        elif silence_report.status in ("skipped_no_audio_source", "blocked"):
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_detection",
                event_type="SILENCE_DETECTION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=silence_report.recommendation or "silence_detection_skipped",
                details={
                    "status": silence_report.status,
                    "recommendation": silence_report.recommendation,
                    "warnings": list(silence_report.warnings or []),
                    "errors": list(silence_report.errors or []),
                },
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_detection",
                event_type="SILENCE_DETECTION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=silence_report.recommendation or "silence_detection_failed",
                details={
                    "status": silence_report.status,
                    "recommendation": silence_report.recommendation,
                    "warnings": list(silence_report.warnings or []),
                    "errors": list(silence_report.errors or []),
                },
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="silence_detection_done",
        reason="silence_detection_completed_or_skipped",
    )

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="silence_classification",
        event_type="SILENCE_CLASSIFICATION_STARTED",
        action="run_silence_classifier",
        reason="silence_classification_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "silence_detection_status": getattr(job, "silence_detection_status", None),
            "silence_segment_count": int(getattr(job, "silence_segment_count", 0) or 0),
        },
    )

    try:
        _rms_context_timeline = list(getattr(job, "rms_energy_context_timeline", None) or [])
        silence_classifier_report = run_silence_classifier_for_job(
            job=job,
            profile=json_profile if isinstance(json_profile, dict) else None,
            energy_timeline=_rms_context_timeline if _rms_context_timeline else None,
            metadata={
                "stage": "2B-07-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as classifier_exc:
        silence_classifier_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="silence_classification",
            event_type="SILENCE_CLASSIFICATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="silence_classifier_runner_exception",
            details={"error": str(classifier_exc)},
        )

    if silence_classifier_report is not None:
        job.silence_classification_report = silence_classifier_report.to_dict()
        job.silence_classification_result = dict(silence_classifier_report.classification_result or {})
        job.silence_classification_status = silence_classifier_report.status
        job.silence_classifications = list(silence_classifier_report.classifications or [])
        job.silence_classification_count = int(silence_classifier_report.classification_count or 0)
        job.silence_remove_candidate_count = int(silence_classifier_report.remove_candidate_count or 0)
        job.silence_keep_candidate_count = int(silence_classifier_report.keep_candidate_count or 0)
        job.silence_counts_by_classification = dict(silence_classifier_report.counts_by_classification or {})

        classifier_details = {
            "status": silence_classifier_report.status,
            "classification_count": silence_classifier_report.classification_count,
            "remove_candidate_count": silence_classifier_report.remove_candidate_count,
            "keep_candidate_count": silence_classifier_report.keep_candidate_count,
            "counts_by_classification": dict(silence_classifier_report.counts_by_classification or {}),
            "recommendation": silence_classifier_report.recommendation,
            "warnings": list(silence_classifier_report.warnings or []),
            "errors": list(silence_classifier_report.errors or []),
        }

        if silence_classifier_report.status == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_classification",
                event_type="SILENCE_CLASSIFICATION_DONE",
                action="continue_pipeline",
                reason="silence_classification_completed",
                details=classifier_details,
            )
        elif silence_classifier_report.status == "skipped_no_silence_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_classification",
                event_type="SILENCE_CLASSIFICATION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=silence_classifier_report.recommendation or "silence_classification_skipped",
                details=classifier_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="silence_classification",
                event_type="SILENCE_CLASSIFICATION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=silence_classifier_report.recommendation or "silence_classification_failed",
                details=classifier_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="silence_classification_done",
        reason="silence_classification_completed_or_skipped",
    )

    # ── Transcript Lifeline (3-B) ─────────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="transcript",
        event_type="TRANSCRIPT_STARTED",
        action="run_transcript",
        reason="transcript_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "speech_audio_ready": "speech_audio"
            in list(getattr(job, "ready_audio_targets", []) or []),
        },
    )

    try:
        transcript_run_report = run_transcript_for_job(
            job=job,
            allow_raw_video_fallback=True,
            require_existing_file=True,
            metadata={
                "stage": "3-B",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as transcript_exc:
        transcript_run_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="transcript",
            event_type="TRANSCRIPT_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="transcript_runner_exception",
            details={"error": str(transcript_exc)},
        )

    if transcript_run_report is not None:
        apply_transcript_run_report_to_job(job, transcript_run_report)

        _transcript_details = {
            "status": transcript_run_report.status,
            "source_type": transcript_run_report.source_type,
            "source_path": transcript_run_report.source_path,
            "segment_count": transcript_run_report.segment_count,
            "word_count": transcript_run_report.word_count,
            "duration_seconds": transcript_run_report.duration_seconds,
            "language": transcript_run_report.language,
            "engine": transcript_run_report.engine,
            "recommendation": transcript_run_report.recommendation,
            "warnings": list(transcript_run_report.warnings or []),
            "errors": list(transcript_run_report.errors or []),
        }

        _transcript_status_text = str(transcript_run_report.status or "").strip().lower()

        if _transcript_status_text == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transcript",
                event_type="TRANSCRIPT_DONE",
                action="continue_pipeline",
                reason="transcript_completed",
                details=_transcript_details,
            )
        elif _transcript_status_text == "completed_with_warnings":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transcript",
                event_type="TRANSCRIPT_DONE",
                action="continue_pipeline",
                status="warn",
                reason=transcript_run_report.recommendation
                or "transcript_completed_with_warnings",
                details=_transcript_details,
            )
        elif _transcript_status_text in {
            "blocked_missing_preprocessed_audio",
            "whisper_unavailable",
        }:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transcript",
                event_type="TRANSCRIPT_BLOCKED",
                action="continue_pipeline",
                status="warn",
                reason=transcript_run_report.recommendation
                or _transcript_status_text,
                details=_transcript_details,
            )
        elif _transcript_status_text == "skipped_no_audio_source":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transcript",
                event_type="TRANSCRIPT_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=transcript_run_report.recommendation or "transcript_skipped",
                details=_transcript_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transcript",
                event_type="TRANSCRIPT_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=transcript_run_report.recommendation or "transcript_failed",
                details=_transcript_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="transcript_done",
        reason="transcript_completed_or_skipped",
    )
    # ── End Transcript Lifeline ───────────────────────────────────────────

    # ── Filler Word Detection (2B-10-C) ───────────────────────────────────
    # Sentence Boundary Protection (2B-20-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="sentence_boundary",
        event_type="SENTENCE_BOUNDARY_STARTED",
        action="run_sentence_boundary",
        reason="sentence_boundary_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
        },
    )

    try:
        sentence_boundary_report = run_sentence_boundary_for_job(
            job=job,
            metadata={
                "stage": "2B-20-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_sentence_boundary_run_report_to_job(job, sentence_boundary_report)
    except Exception as sentence_boundary_exc:
        sentence_boundary_report = None
        job.sentence_boundary_status = "failed"
        job.sentence_boundary_recommendation = "sentence_boundary_failed"
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="sentence_boundary",
            event_type="SENTENCE_BOUNDARY_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="sentence_boundary_runner_exception",
            details={"error": str(sentence_boundary_exc)},
        )

    if sentence_boundary_report is not None:
        _sentence_boundary_details = {
            "status": sentence_boundary_report.status,
            "boundary_count": sentence_boundary_report.boundary_count,
            "protection_zone_count": sentence_boundary_report.protection_zone_count,
            "complete_sentence_count": sentence_boundary_report.complete_sentence_count,
            "open_fragment_count": sentence_boundary_report.open_fragment_count,
            "question_count": sentence_boundary_report.question_count,
            "open_question_count": sentence_boundary_report.open_question_count,
            "safe_boundary_count": sentence_boundary_report.safe_boundary_count,
            "unsafe_boundary_count": sentence_boundary_report.unsafe_boundary_count,
            "recommendation": sentence_boundary_report.recommendation,
            "warnings": list(sentence_boundary_report.warnings or []),
            "errors": list(sentence_boundary_report.errors or []),
        }
        _sentence_boundary_status = str(
            sentence_boundary_report.status or ""
        ).strip().lower()

        if _sentence_boundary_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="sentence_boundary",
                event_type="SENTENCE_BOUNDARY_DONE",
                action="continue_pipeline",
                status="warn"
                if _sentence_boundary_status == "completed_with_warnings"
                else "ok",
                reason=sentence_boundary_report.recommendation
                or "sentence_boundary_completed",
                details=_sentence_boundary_details,
            )
        elif _sentence_boundary_status == "skipped_no_transcript_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="sentence_boundary",
                event_type="SENTENCE_BOUNDARY_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=sentence_boundary_report.recommendation
                or "sentence_boundary_skipped_no_transcript",
                details=_sentence_boundary_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="sentence_boundary",
                event_type="SENTENCE_BOUNDARY_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=sentence_boundary_report.recommendation
                or "sentence_boundary_failed",
                details=_sentence_boundary_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="sentence_boundary_done",
        reason="sentence_boundary_completed_or_skipped",
    )
    # End Sentence Boundary Protection

    # Keyword Emotion Scoring (2B-21-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="keyword_emotion",
        event_type="KEYWORD_EMOTION_STARTED",
        action="run_keyword_emotion",
        reason="keyword_emotion_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
        },
    )

    try:
        keyword_emotion_report = run_keyword_emotion_for_job(
            job=job,
            metadata={
                "stage": "2B-21-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_keyword_emotion_run_report_to_job(job, keyword_emotion_report)
    except Exception as keyword_emotion_exc:
        keyword_emotion_report = None
        job.keyword_emotion_status = "failed"
        job.keyword_emotion_recommendation = "keyword_emotion_failed"
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="keyword_emotion",
            event_type="KEYWORD_EMOTION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="keyword_emotion_runner_exception",
            details={"error": str(keyword_emotion_exc)},
        )

    if keyword_emotion_report is not None:
        _keyword_emotion_details = {
            "status": keyword_emotion_report.status,
            "match_count": keyword_emotion_report.match_count,
            "segment_score_count": keyword_emotion_report.segment_score_count,
            "hype_match_count": keyword_emotion_report.hype_match_count,
            "frustration_match_count": keyword_emotion_report.frustration_match_count,
            "shock_match_count": keyword_emotion_report.shock_match_count,
            "laugh_match_count": keyword_emotion_report.laugh_match_count,
            "question_match_count": keyword_emotion_report.question_match_count,
            "high_value_segment_count": keyword_emotion_report.high_value_segment_count,
            "recommendation": keyword_emotion_report.recommendation,
            "warnings": list(keyword_emotion_report.warnings or []),
            "errors": list(keyword_emotion_report.errors or []),
        }
        _keyword_emotion_status = str(keyword_emotion_report.status or "").strip().lower()

        if _keyword_emotion_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="keyword_emotion",
                event_type="KEYWORD_EMOTION_DONE",
                action="continue_pipeline",
                status="warn"
                if _keyword_emotion_status == "completed_with_warnings"
                else "ok",
                reason=keyword_emotion_report.recommendation
                or "keyword_emotion_completed",
                details=_keyword_emotion_details,
            )
        elif _keyword_emotion_status == "skipped_no_transcript_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="keyword_emotion",
                event_type="KEYWORD_EMOTION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=keyword_emotion_report.recommendation
                or "keyword_emotion_skipped_no_transcript",
                details=_keyword_emotion_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="keyword_emotion",
                event_type="KEYWORD_EMOTION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=keyword_emotion_report.recommendation
                or "keyword_emotion_failed",
                details=_keyword_emotion_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="keyword_emotion_done",
        reason="keyword_emotion_completed_or_skipped",
    )
    # End Keyword Emotion Scoring

    # Interaction Classification (2B-22-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="interaction_classification",
        event_type="INTERACTION_CLASSIFICATION_STARTED",
        action="run_interaction_classification",
        reason="interaction_classification_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
        },
    )

    try:
        interaction_classification_report = run_interaction_classification_for_job(
            job=job,
            metadata={
                "stage": "2B-22-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_interaction_classification_run_report_to_job(
            job,
            interaction_classification_report,
        )
    except Exception as interaction_classification_exc:
        interaction_classification_report = None
        job.interaction_classification_status = "failed"
        job.interaction_classification_recommendation = (
            "interaction_classification_failed"
        )
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="interaction_classification",
            event_type="INTERACTION_CLASSIFICATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="interaction_classification_runner_exception",
            details={"error": str(interaction_classification_exc)},
        )

    if interaction_classification_report is not None:
        _interaction_classification_details = {
            "status": interaction_classification_report.status,
            "point_count": interaction_classification_report.point_count,
            "segment_classification_count": (
                interaction_classification_report.segment_classification_count
            ),
            "monologue_count": interaction_classification_report.monologue_count,
            "interaction_count": interaction_classification_report.interaction_count,
            "question_answer_count": (
                interaction_classification_report.question_answer_count
            ),
            "chat_reaction_count": (
                interaction_classification_report.chat_reaction_count
            ),
            "callout_count": interaction_classification_report.callout_count,
            "private_or_meta_count": (
                interaction_classification_report.private_or_meta_count
            ),
            "context_needed_count": (
                interaction_classification_report.context_needed_count
            ),
            "recommendation": interaction_classification_report.recommendation,
            "warnings": list(interaction_classification_report.warnings or []),
            "errors": list(interaction_classification_report.errors or []),
        }
        _interaction_classification_status = str(
            interaction_classification_report.status or ""
        ).strip().lower()

        if _interaction_classification_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="interaction_classification",
                event_type="INTERACTION_CLASSIFICATION_DONE",
                action="continue_pipeline",
                status="warn"
                if _interaction_classification_status == "completed_with_warnings"
                else "ok",
                reason=interaction_classification_report.recommendation
                or "interaction_classification_completed",
                details=_interaction_classification_details,
            )
        elif _interaction_classification_status == "skipped_no_transcript_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="interaction_classification",
                event_type="INTERACTION_CLASSIFICATION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=interaction_classification_report.recommendation
                or "interaction_classification_skipped_no_transcript",
                details=_interaction_classification_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="interaction_classification",
                event_type="INTERACTION_CLASSIFICATION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=interaction_classification_report.recommendation
                or "interaction_classification_failed",
                details=_interaction_classification_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="interaction_classification_done",
        reason="interaction_classification_completed_or_skipped",
    )
    # End Interaction Classification

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="filler_word_detection",
        event_type="FILLER_WORD_DETECTION_STARTED",
        action="run_filler_word_detection",
        reason="filler_word_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    try:
        filler_word_report = run_filler_word_detection_for_job(
            job=job,
            detect_repeated_words=True,
            repeat_max_gap_seconds=0.35,
            max_occurrences=None,
            metadata={
                "stage": "2B-10-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as filler_exc:
        filler_word_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="filler_word_detection",
            event_type="FILLER_WORD_DETECTION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="filler_word_runner_exception",
            details={"error": str(filler_exc)},
        )

    if filler_word_report is not None:
        job.filler_word_report = filler_word_report.to_dict()
        job.filler_word_status = filler_word_report.status
        job.filler_word_transcript_source = filler_word_report.transcript_source
        job.filler_word_detection_result = dict(filler_word_report.detection_result or {})
        job.filler_word_occurrences = list(filler_word_report.occurrences or [])
        job.filler_word_occurrence_count = int(filler_word_report.occurrence_count or 0)
        job.filler_word_remove_candidate_count = int(filler_word_report.remove_candidate_count or 0)
        job.filler_word_counts_by_type = dict(filler_word_report.counts_by_filler_type or {})
        job.filler_word_counts_by_language = dict(filler_word_report.counts_by_language or {})
        job.filler_word_total_duration_seconds = float(filler_word_report.total_filler_duration_seconds or 0.0)
        job.filler_word_transcript_word_count = int(filler_word_report.transcript_word_count or 0)
        job.filler_word_rate = float(filler_word_report.filler_rate or 0.0)
        job.filler_word_recommendation = filler_word_report.recommendation

        _filler_details = {
            "status": filler_word_report.status,
            "transcript_source": filler_word_report.transcript_source,
            "occurrence_count": filler_word_report.occurrence_count,
            "remove_candidate_count": filler_word_report.remove_candidate_count,
            "counts_by_filler_type": dict(filler_word_report.counts_by_filler_type or {}),
            "counts_by_language": dict(filler_word_report.counts_by_language or {}),
            "transcript_word_count": filler_word_report.transcript_word_count,
            "filler_rate": filler_word_report.filler_rate,
            "recommendation": filler_word_report.recommendation,
            "warnings": list(filler_word_report.warnings or []),
            "errors": list(filler_word_report.errors or []),
        }

        if filler_word_report.status == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="filler_word_detection",
                event_type="FILLER_WORD_DETECTION_DONE",
                action="continue_pipeline",
                reason="filler_word_detection_completed",
                details=_filler_details,
            )
        elif filler_word_report.status == "completed_with_warnings":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="filler_word_detection",
                event_type="FILLER_WORD_DETECTION_COMPLETED_WITH_WARNINGS",
                action="continue_pipeline",
                status="warn",
                reason=filler_word_report.recommendation or "filler_word_detection_completed_with_warnings",
                details=_filler_details,
            )
        elif filler_word_report.status == "skipped_no_transcript":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="filler_word_detection",
                event_type="FILLER_WORD_DETECTION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=filler_word_report.recommendation or "filler_word_detection_skipped",
                details=_filler_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="filler_word_detection",
                event_type="FILLER_WORD_DETECTION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=filler_word_report.recommendation or "filler_word_detection_failed",
                details=_filler_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="filler_word_detection_done",
        reason="filler_word_detection_completed_or_skipped",
    )

    # Dead Content Detection (2B-23-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="dead_content_detection",
        event_type="DEAD_CONTENT_STARTED",
        action="run_dead_content_detection",
        reason="dead_content_detection_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
            "have_filler_word_report": bool(getattr(job, "filler_word_report", None)),
            "have_keyword_emotion_report": bool(
                getattr(job, "keyword_emotion_report", None)
            ),
            "have_interaction_classification_report": bool(
                getattr(job, "interaction_classification_report", None)
            ),
        },
    )

    try:
        dead_content_report = run_dead_content_detection_for_job(
            job=job,
            metadata={
                "stage": "2B-23-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_dead_content_run_report_to_job(job, dead_content_report)
    except Exception as dead_content_exc:
        dead_content_report = None
        job.dead_content_status = "failed"
        job.dead_content_recommendation = "dead_content_detection_failed"
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="dead_content_detection",
            event_type="DEAD_CONTENT_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="dead_content_detection_exception",
            details={"error": str(dead_content_exc)},
        )

    if dead_content_report is not None:
        _dead_content_details = {
            "status": dead_content_report.status,
            "candidate_count": dead_content_report.candidate_count,
            "segment_score_count": dead_content_report.segment_score_count,
            "dead_air_candidate_count": (
                dead_content_report.dead_air_candidate_count
            ),
            "low_value_candidate_count": (
                dead_content_report.low_value_candidate_count
            ),
            "filler_pause_candidate_count": (
                dead_content_report.filler_pause_candidate_count
            ),
            "loading_or_menu_candidate_count": (
                dead_content_report.loading_or_menu_candidate_count
            ),
            "private_or_meta_candidate_count": (
                dead_content_report.private_or_meta_candidate_count
            ),
            "protected_candidate_count": dead_content_report.protected_candidate_count,
            "high_confidence_candidate_count": (
                dead_content_report.high_confidence_candidate_count
            ),
            "recommendation": dead_content_report.recommendation,
            "warnings": list(dead_content_report.warnings or []),
            "errors": list(dead_content_report.errors or []),
        }
        _dead_content_status = str(dead_content_report.status or "").strip().lower()

        if _dead_content_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="dead_content_detection",
                event_type="DEAD_CONTENT_DONE",
                action="continue_pipeline",
                status="warn"
                if _dead_content_status == "completed_with_warnings"
                else "ok",
                reason=dead_content_report.recommendation
                or "dead_content_detection_completed",
                details=_dead_content_details,
            )
        elif _dead_content_status == "skipped_no_inputs":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="dead_content_detection",
                event_type="DEAD_CONTENT_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=dead_content_report.recommendation
                or "dead_content_skipped_no_inputs",
                details=_dead_content_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="dead_content_detection",
                event_type="DEAD_CONTENT_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=dead_content_report.recommendation
                or "dead_content_detection_failed",
                details=_dead_content_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="dead_content_done",
        reason="dead_content_detection_completed_or_skipped",
    )
    # End Dead Content Detection
    # ── End Filler Word Detection ─────────────────────────────────────────

    # ── Audio Normalization (2B-11-E) ─────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="audio_normalization",
        event_type="AUDIO_NORMALIZATION_STARTED",
        action="run_audio_normalization",
        reason="audio_normalization_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    try:
        audio_normalization_report = run_audio_normalization_for_job(
            job=job,
            target_rms_dbfs=-18.0,
            target_peak_dbfs=-1.0,
            require_existing_file=True,
            allow_original_wav_fallback=True,
            metadata={
                "stage": "2B-11-E",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as audio_normalization_exc:
        audio_normalization_report = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="audio_normalization",
            event_type="AUDIO_NORMALIZATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="audio_normalization_runner_exception",
            details={"error": str(audio_normalization_exc)},
        )

    if audio_normalization_report is not None:
        _apply_audio_normalization_report_to_job(job, audio_normalization_report)

        _audio_normalization_event_type = _audio_normalization_event_type_for_status(
            audio_normalization_report.status
        )
        _audio_normalization_status = (
            "warn"
            if _audio_normalization_event_type
            in {
                "AUDIO_NORMALIZATION_COMPLETED_WITH_WARNINGS",
                "AUDIO_NORMALIZATION_BLOCKED",
                "AUDIO_NORMALIZATION_SKIPPED",
                "AUDIO_NORMALIZATION_FAILED",
            }
            else "ok"
        )

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="audio_normalization",
            event_type=_audio_normalization_event_type,
            action="continue_pipeline",
            status=_audio_normalization_status,
            reason=audio_normalization_report.recommendation
            or "audio_normalization_completed_or_skipped",
            details=_audio_normalization_decision_details(audio_normalization_report),
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="audio_normalization_done",
        reason="audio_normalization_completed_or_skipped",
    )
    # ── End Audio Normalization ─────────────────────────────────────────

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="analyzing",
        reason="pipeline_analysis_started",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="beat_detection",
        event_type="BEAT_DETECTION_STARTED",
        action="run_beat_detection",
        reason="beat_detection_runner_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "profile_id": getattr(job, "profile_id", None),
            "quality_mode": getattr(job, "quality_mode", None),
        },
    )

    beat_detection_report = run_beat_detection_for_job(
        job=job,
        frame_ms=50.0,
        hop_ms=25.0,
        peak_threshold=1.35,
        min_beat_distance_seconds=0.25,
        require_existing_file=True,
        allow_original_wav_fallback=True,
        metadata={
            "stage": "2B-12-E",
            "job_id": getattr(job, "job_id", None),
        },
    )

    _apply_beat_detection_report_to_job(job, beat_detection_report)

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="beat_detection",
        event_type=_beat_detection_event_type_for_status(
            getattr(beat_detection_report, "status", None)
        ),
        action="complete_beat_detection",
        status=(
            "warning"
            if getattr(beat_detection_report, "status", None)
            in {
                "completed_with_warnings",
                "blocked_missing_preprocessed_audio",
                "skipped_unsupported_source",
                "skipped_no_audio_source",
            }
            else getattr(beat_detection_report, "status", "ok")
        ),
        reason="beat_detection_completed_or_skipped",
        details=_beat_detection_decision_details(beat_detection_report),
    )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="beat_detection_done",
        reason="beat_detection_completed_or_skipped",
    )

    # ── Unified Edit Signal Registry (3-C) ────────────────────────────────
    # Content Value Score (2B-24-C)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="content_value",
        event_type="CONTENT_VALUE_STARTED",
        action="run_content_value",
        reason="content_value_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
            "have_dead_content_report": bool(getattr(job, "dead_content_report", None)),
            "have_keyword_emotion_report": bool(
                getattr(job, "keyword_emotion_report", None)
            ),
            "have_interaction_classification_report": bool(
                getattr(job, "interaction_classification_report", None)
            ),
            "have_visual_energy_report": bool(
                getattr(job, "visual_energy_report", None)
            ),
            "have_energy_peak_report": bool(getattr(job, "energy_peak_report", None)),
            "have_audio_normalization_report": bool(
                getattr(job, "audio_normalization_report", None)
            ),
        },
    )

    try:
        content_value_report = run_content_value_for_job(
            job=job,
            metadata={
                "stage": "2B-24-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_content_value_run_report_to_job(job, content_value_report)
    except Exception as content_value_exc:
        content_value_report = None
        job.content_value_status = "failed"
        job.content_value_recommendation = "content_value_failed"
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="content_value",
            event_type="CONTENT_VALUE_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="content_value_exception",
            details={"error": str(content_value_exc)},
        )

    if content_value_report is not None:
        _content_value_details = {
            "status": content_value_report.status,
            "segment_score_count": content_value_report.segment_score_count,
            "high_value_count": content_value_report.high_value_count,
            "mid_value_count": content_value_report.mid_value_count,
            "low_value_count": content_value_report.low_value_count,
            "protected_context_count": content_value_report.protected_context_count,
            "hook_candidate_count": content_value_report.hook_candidate_count,
            "technical_warning_count": (
                content_value_report.technical_warning_count
            ),
            "avg_content_value_score": content_value_report.avg_content_value_score,
            "max_content_value_score": content_value_report.max_content_value_score,
            "min_content_value_score": content_value_report.min_content_value_score,
            "recommendation": content_value_report.recommendation,
            "warnings": list(content_value_report.warnings or []),
            "errors": list(content_value_report.errors or []),
        }
        _content_value_status = str(content_value_report.status or "").strip().lower()

        if _content_value_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="content_value",
                event_type="CONTENT_VALUE_DONE",
                action="continue_pipeline",
                status="warn"
                if _content_value_status == "completed_with_warnings"
                else "ok",
                reason=content_value_report.recommendation
                or "content_value_completed",
                details=_content_value_details,
            )
        elif _content_value_status == "skipped_no_inputs":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="content_value",
                event_type="CONTENT_VALUE_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=content_value_report.recommendation
                or "content_value_skipped_no_inputs",
                details=_content_value_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="content_value",
                event_type="CONTENT_VALUE_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=content_value_report.recommendation or "content_value_failed",
                details=_content_value_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="content_value_done",
        reason="content_value_completed_or_skipped",
    )
    # End Content Value Score

    # Profanity Censor SFX Signal Foundation (2B-24.5)
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="profanity_censor",
        event_type="PROFANITY_CENSOR_STARTED",
        action="run_profanity_censor",
        reason="profanity_censor_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transcript_segment_count": len(
                list(getattr(job, "transcript_segments", []) or [])
            ),
        },
    )

    try:
        profanity_censor_report = run_profanity_censor_for_job(
            job=job,
            metadata={
                "stage": "2B-24.5",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_profanity_censor_run_report_to_job(job, profanity_censor_report)
    except Exception as profanity_censor_exc:
        profanity_censor_report = None
        job.profanity_censor_status = "failed"
        job.profanity_censor_recommendation = "profanity_censor_failed"
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="profanity_censor",
            event_type="PROFANITY_CENSOR_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="profanity_censor_exception",
            details={"error": str(profanity_censor_exc)},
        )

    if profanity_censor_report is not None:
        _profanity_censor_details = {
            "status": profanity_censor_report.status,
            "match_count": profanity_censor_report.match_count,
            "severe_match_count": profanity_censor_report.severe_match_count,
            "mild_match_count": profanity_censor_report.mild_match_count,
            "censor_required_count": profanity_censor_report.censor_required_count,
            "word_level_match_count": profanity_censor_report.word_level_match_count,
            "segment_fallback_match_count": (
                profanity_censor_report.segment_fallback_match_count
            ),
            "recommendation": profanity_censor_report.recommendation,
            "warnings": list(profanity_censor_report.warnings or []),
            "errors": list(profanity_censor_report.errors or []),
        }
        _profanity_censor_status = str(
            profanity_censor_report.status or ""
        ).strip().lower()

        if _profanity_censor_status in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="profanity_censor",
                event_type="PROFANITY_CENSOR_DONE",
                action="continue_pipeline",
                status="warn"
                if _profanity_censor_status == "completed_with_warnings"
                else "ok",
                reason=profanity_censor_report.recommendation
                or "profanity_censor_completed",
                details=_profanity_censor_details,
            )
        elif _profanity_censor_status == "skipped_no_transcript_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="profanity_censor",
                event_type="PROFANITY_CENSOR_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=profanity_censor_report.recommendation
                or "profanity_censor_skipped_no_transcript",
                details=_profanity_censor_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="profanity_censor",
                event_type="PROFANITY_CENSOR_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=profanity_censor_report.recommendation
                or "profanity_censor_failed",
                details=_profanity_censor_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="profanity_censor_done",
        reason="profanity_censor_completed_or_skipped",
    )
    # End Profanity Censor SFX Signal Foundation

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="unified_edit_signals",
        event_type="UNIFIED_EDIT_SIGNALS_STARTED",
        action="run_unified_edit_signal_registry",
        reason="unified_edit_signals_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "have_energy_peak_report": bool(getattr(job, "energy_peak_report", None)),
            "have_filler_word_report": bool(getattr(job, "filler_word_report", None)),
            "have_audio_normalization_report": bool(
                getattr(job, "audio_normalization_report", None)
            ),
            "have_beat_detection_report": bool(getattr(job, "beat_detection_report", None)),
        },
    )

    try:
        unified_signal_result = run_unified_edit_signal_registry_for_job(
            job=job,
            metadata={
                "stage": "3-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
    except Exception as unified_signal_exc:
        unified_signal_result = None
        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="unified_edit_signals",
            event_type="UNIFIED_EDIT_SIGNALS_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="unified_edit_signal_registry_exception",
            details={"error": str(unified_signal_exc)},
        )

    if unified_signal_result is not None:
        _unified_signal_details = {
            "status": unified_signal_result.status,
            "signal_count": unified_signal_result.signal_count,
            "source_counts": dict(unified_signal_result.source_counts),
            "type_counts": dict(unified_signal_result.type_counts),
            "priority_counts": dict(unified_signal_result.priority_counts),
            "duplicate_count": unified_signal_result.duplicate_count,
            "max_signal_score": unified_signal_result.max_signal_score,
            "avg_signal_score": unified_signal_result.avg_signal_score,
            "timeline_coverage_seconds": unified_signal_result.timeline_coverage_seconds,
            "recommendation": unified_signal_result.recommendation,
            "warnings": list(unified_signal_result.warnings or []),
            "errors": list(unified_signal_result.errors or []),
        }

        _unified_status_text = str(unified_signal_result.status or "").strip().lower()

        if _unified_status_text == "ok":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="unified_edit_signals",
                event_type="UNIFIED_EDIT_SIGNALS_DONE",
                action="continue_pipeline",
                reason="unified_edit_signals_completed",
                details=_unified_signal_details,
            )
        elif _unified_status_text == "completed_with_warnings":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="unified_edit_signals",
                event_type="UNIFIED_EDIT_SIGNALS_DONE",
                action="continue_pipeline",
                status="warn",
                reason=unified_signal_result.recommendation
                or "unified_edit_signals_completed_with_warnings",
                details=_unified_signal_details,
            )
        elif _unified_status_text == "skipped_no_signals":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="unified_edit_signals",
                event_type="UNIFIED_EDIT_SIGNALS_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=unified_signal_result.recommendation
                or "no_edit_signals_available",
                details=_unified_signal_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="unified_edit_signals",
                event_type="UNIFIED_EDIT_SIGNALS_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=unified_signal_result.recommendation or "unified_edit_signals_failed",
                details=_unified_signal_details,
            )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="unified_edit_signals_done",
        reason="unified_edit_signals_completed_or_skipped",
    )
    # ── End Unified Edit Signal Registry ──────────────────────────────────

    # ── Segment Classification (2B-25-C) ─────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="segment_classification",
        event_type="SEGMENT_CLASSIFICATION_STARTED",
        action="run_segment_classification",
        reason="segment_classification_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "unified_edit_signal_count": int(
                getattr(job, "unified_edit_signal_count", 0) or 0
            ),
        },
    )

    try:
        segment_classification_report = run_segment_classification_for_job(
            job=job,
            metadata={
                "stage": "2B-25-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_segment_classification_run_report_to_job(
            job=job,
            report=segment_classification_report,
        )

        _segment_classification_details = {
            "status": segment_classification_report.status,
            "segment_count": segment_classification_report.segment_count,
            "highlight_count": segment_classification_report.highlight_count,
            "hook_candidate_count": segment_classification_report.hook_candidate_count,
            "protected_context_count": (
                segment_classification_report.protected_context_count
            ),
            "dead_candidate_count": segment_classification_report.dead_candidate_count,
            "filler_count": segment_classification_report.filler_count,
            "transition_count": segment_classification_report.transition_count,
            "censor_required_count": (
                segment_classification_report.censor_required_count
            ),
            "technical_warning_count": (
                segment_classification_report.technical_warning_count
            ),
            "recommendation": segment_classification_report.recommendation,
            "warnings": list(segment_classification_report.warnings or []),
            "errors": list(segment_classification_report.errors or []),
        }

        _segment_classification_status_text = str(
            segment_classification_report.status or ""
        ).strip().lower()

        if _segment_classification_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="segment_classification",
                event_type="SEGMENT_CLASSIFICATION_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _segment_classification_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=segment_classification_report.recommendation
                or "segment_classification_completed",
                details=_segment_classification_details,
            )
        elif _segment_classification_status_text == "skipped_no_unified_signals":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="segment_classification",
                event_type="SEGMENT_CLASSIFICATION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=segment_classification_report.recommendation
                or "segment_classifier_skipped_no_unified_signals",
                details=_segment_classification_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="segment_classification",
                event_type="SEGMENT_CLASSIFICATION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=segment_classification_report.recommendation
                or "segment_classification_failed",
                details=_segment_classification_details,
            )

    except Exception as segment_classification_exc:
        job.segment_classification_status = "failed"
        job.segment_classification_recommendation = "segment_classification_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="segment_classification",
            event_type="SEGMENT_CLASSIFICATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="segment_classification_exception",
            details={"error": str(segment_classification_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="segment_classification_done",
        reason="segment_classification_completed_or_skipped",
    )
    # ── End Segment Classification ─────────────────────────────────────────
    # ── Murch Scoring (2B-26-C) ───────────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="murch_scoring",
        event_type="MURCH_SCORING_STARTED",
        action="run_murch_scoring",
        reason="murch_scoring_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "segment_classification_segment_count": int(
                getattr(job, "segment_classification_segment_count", 0) or 0
            ),
        },
    )

    try:
        murch_scoring_report = run_murch_scoring_for_job(
            job=job,
            metadata={
                "stage": "2B-26-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_murch_scoring_run_report_to_job(
            job=job,
            report=murch_scoring_report,
        )

        _murch_scoring_details = {
            "status": murch_scoring_report.status,
            "segment_score_count": murch_scoring_report.segment_score_count,
            "high_score_count": murch_scoring_report.high_score_count,
            "medium_score_count": murch_scoring_report.medium_score_count,
            "low_score_count": murch_scoring_report.low_score_count,
            "protected_context_count": murch_scoring_report.protected_context_count,
            "censor_required_count": murch_scoring_report.censor_required_count,
            "technical_warning_count": murch_scoring_report.technical_warning_count,
            "avg_murch_score": murch_scoring_report.avg_murch_score,
            "max_murch_score": murch_scoring_report.max_murch_score,
            "min_murch_score": murch_scoring_report.min_murch_score,
            "recommendation": murch_scoring_report.recommendation,
            "warnings": list(murch_scoring_report.warnings or []),
            "errors": list(murch_scoring_report.errors or []),
        }

        _murch_scoring_status_text = str(
            murch_scoring_report.status or ""
        ).strip().lower()

        if _murch_scoring_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="murch_scoring",
                event_type="MURCH_SCORING_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _murch_scoring_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=murch_scoring_report.recommendation
                or "murch_scoring_completed",
                details=_murch_scoring_details,
            )
        elif _murch_scoring_status_text == "skipped_no_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="murch_scoring",
                event_type="MURCH_SCORING_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=murch_scoring_report.recommendation
                or "murch_scoring_skipped_no_segments",
                details=_murch_scoring_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="murch_scoring",
                event_type="MURCH_SCORING_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=murch_scoring_report.recommendation
                or "murch_scoring_failed",
                details=_murch_scoring_details,
            )

    except Exception as murch_scoring_exc:
        job.murch_scoring_status = "failed"
        job.murch_scoring_recommendation = "murch_scoring_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="murch_scoring",
            event_type="MURCH_SCORING_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="murch_scoring_exception",
            details={"error": str(murch_scoring_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="murch_scoring_done",
        reason="murch_scoring_completed_or_skipped",
    )
    # ── End Murch Scoring ─────────────────────────────────────────────────

    # ── Cut List Generation (2B-27-C) ─────────────────────────────────────
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="cut_list_generation",
        event_type="CUT_LIST_GENERATION_STARTED",
        action="run_cut_list_generation",
        reason="cut_list_generation_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "segment_classification_segment_count": int(
                getattr(job, "segment_classification_segment_count", 0) or 0
            ),
            "murch_scoring_segment_score_count": int(
                getattr(job, "murch_scoring_segment_score_count", 0) or 0
            ),
        },
    )

    try:
        cut_list_report = run_cut_list_generation_for_job(
            job=job,
            metadata={
                "stage": "2B-27-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_cut_list_run_report_to_job(
            job=job,
            report=cut_list_report,
        )

        _cut_list_details = {
            "status": cut_list_report.status,
            "item_count": cut_list_report.item_count,
            "keep_count": cut_list_report.keep_count,
            "review_keep_count": cut_list_report.review_keep_count,
            "review_trim_count": cut_list_report.review_trim_count,
            "review_remove_count": cut_list_report.review_remove_count,
            "protect_count": cut_list_report.protect_count,
            "censor_keep_count": cut_list_report.censor_keep_count,
            "technical_review_count": cut_list_report.technical_review_count,
            "unknown_review_count": cut_list_report.unknown_review_count,
            "recommendation": cut_list_report.recommendation,
            "warnings": list(cut_list_report.warnings or []),
            "errors": list(cut_list_report.errors or []),
        }

        _cut_list_status_text = str(cut_list_report.status or "").strip().lower()

        if _cut_list_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="cut_list_generation",
                event_type="CUT_LIST_GENERATION_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _cut_list_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=cut_list_report.recommendation
                or "cut_list_generation_completed",
                details=_cut_list_details,
            )
        elif _cut_list_status_text == "skipped_no_segments":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="cut_list_generation",
                event_type="CUT_LIST_GENERATION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=cut_list_report.recommendation
                or "cut_list_generation_skipped_no_segments",
                details=_cut_list_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="cut_list_generation",
                event_type="CUT_LIST_GENERATION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=cut_list_report.recommendation
                or "cut_list_generation_failed",
                details=_cut_list_details,
            )

    except Exception as cut_list_generation_exc:
        job.cut_list_status = "failed"
        job.cut_list_recommendation = "cut_list_generation_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="cut_list_generation",
            event_type="CUT_LIST_GENERATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="cut_list_generation_exception",
            details={"error": str(cut_list_generation_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="cut_list_generation_done",
        reason="cut_list_generation_completed_or_skipped",
    )
    # ── End Cut List Generation ───────────────────────────────────────────

    # -- Clip Duration Optimization (2B-28-C) ----------------------------------
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="clip_duration_optimization",
        event_type="CLIP_DURATION_OPTIMIZATION_STARTED",
        action="run_clip_duration_optimization",
        reason="clip_duration_optimization_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "cut_list_item_count": int(getattr(job, "cut_list_item_count", 0) or 0),
        },
    )

    try:
        clip_duration_report = run_clip_duration_optimization_for_job(
            job=job,
            metadata={
                "stage": "2B-28-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_clip_duration_run_report_to_job(
            job=job,
            report=clip_duration_report,
        )

        _clip_duration_details = {
            "status": clip_duration_report.status,
            "recommendation_count": clip_duration_report.recommendation_count,
            "duration_ok_count": clip_duration_report.duration_ok_count,
            "too_short_count": clip_duration_report.too_short_count,
            "too_long_count": clip_duration_report.too_long_count,
            "trim_review_count": clip_duration_report.trim_review_count,
            "extend_review_count": clip_duration_report.extend_review_count,
            "protect_duration_count": clip_duration_report.protect_duration_count,
            "censor_keep_count": clip_duration_report.censor_keep_count,
            "technical_review_count": clip_duration_report.technical_review_count,
            "invalid_timing_count": clip_duration_report.invalid_timing_count,
            "recommendation": clip_duration_report.recommendation,
            "warnings": list(clip_duration_report.warnings or []),
            "errors": list(clip_duration_report.errors or []),
        }

        _clip_duration_status_text = str(
            clip_duration_report.status or ""
        ).strip().lower()

        if _clip_duration_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="clip_duration_optimization",
                event_type="CLIP_DURATION_OPTIMIZATION_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _clip_duration_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=clip_duration_report.recommendation
                or "clip_duration_optimization_completed",
                details=_clip_duration_details,
            )
        elif _clip_duration_status_text == "skipped_no_cut_list_items":
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="clip_duration_optimization",
                event_type="CLIP_DURATION_OPTIMIZATION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=clip_duration_report.recommendation
                or "clip_duration_optimization_skipped_no_cut_list_items",
                details=_clip_duration_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="clip_duration_optimization",
                event_type="CLIP_DURATION_OPTIMIZATION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=clip_duration_report.recommendation
                or "clip_duration_optimization_failed",
                details=_clip_duration_details,
            )

    except Exception as clip_duration_optimization_exc:
        job.clip_duration_status = "failed"
        job.clip_duration_recommendation = "clip_duration_optimization_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="clip_duration_optimization",
            event_type="CLIP_DURATION_OPTIMIZATION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="clip_duration_optimization_exception",
            details={"error": str(clip_duration_optimization_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="clip_duration_optimization_done",
        reason="clip_duration_optimization_completed_or_skipped",
    )
    # -- End Clip Duration Optimization ----------------------------------------

    # -- Transition Decision Engine (2B-29-C) ----------------------------------
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="transition_decision",
        event_type="TRANSITION_DECISION_STARTED",
        action="run_transition_decision",
        reason="transition_decision_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "clip_duration_recommendation_count": int(
                getattr(job, "clip_duration_recommendation_count", 0) or 0
            ),
            "cut_list_item_count": int(getattr(job, "cut_list_item_count", 0) or 0),
        },
    )

    try:
        transition_decision_report = run_transition_decision_for_job(
            job=job,
            metadata={
                "stage": "2B-29-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_transition_decision_run_report_to_job(
            job=job,
            report=transition_decision_report,
        )

        _transition_decision_details = {
            "status": transition_decision_report.status,
            "decision_count": transition_decision_report.decision_count,
            "hard_cut_review_count": transition_decision_report.hard_cut_review_count,
            "j_cut_review_count": transition_decision_report.j_cut_review_count,
            "l_cut_review_count": transition_decision_report.l_cut_review_count,
            "quick_fade_review_count": (
                transition_decision_report.quick_fade_review_count
            ),
            "no_cut_protect_count": transition_decision_report.no_cut_protect_count,
            "censor_safe_keep_count": transition_decision_report.censor_safe_keep_count,
            "technical_transition_review_count": (
                transition_decision_report.technical_transition_review_count
            ),
            "unknown_review_count": transition_decision_report.unknown_review_count,
            "recommendation": transition_decision_report.recommendation,
            "warnings": list(transition_decision_report.warnings or []),
            "errors": list(transition_decision_report.errors or []),
            "review_only": True,
        }

        _transition_decision_status_text = str(
            transition_decision_report.status or ""
        ).lower()

        if _transition_decision_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transition_decision",
                event_type="TRANSITION_DECISION_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _transition_decision_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=transition_decision_report.recommendation
                or "transition_decision_completed",
                details=_transition_decision_details,
            )
        elif _transition_decision_status_text in {
            "skipped_no_clip_duration_recommendations",
            "skipped_no_cut_list_items",
        }:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transition_decision",
                event_type="TRANSITION_DECISION_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=transition_decision_report.recommendation
                or "transition_decision_skipped_no_inputs",
                details=_transition_decision_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="transition_decision",
                event_type="TRANSITION_DECISION_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=transition_decision_report.recommendation
                or "transition_decision_failed",
                details=_transition_decision_details,
            )

    except Exception as transition_decision_exc:
        job.transition_decision_status = "failed"
        job.transition_decision_recommendation = "transition_decision_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="transition_decision",
            event_type="TRANSITION_DECISION_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="transition_decision_exception",
            details={"error": str(transition_decision_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="transition_decision_done",
        reason="transition_decision_completed_or_skipped",
    )
    # -- End Transition Decision Engine ----------------------------------------

    # -- Continuity Check (2B-30-C) --------------------------------------------
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="continuity_check",
        event_type="CONTINUITY_CHECK_STARTED",
        action="run_continuity_check",
        reason="continuity_check_started",
        details={
            "job_id": getattr(job, "job_id", None),
            "transition_decision_count": int(
                getattr(job, "transition_decision_count", 0) or 0
            ),
            "cut_list_item_count": int(getattr(job, "cut_list_item_count", 0) or 0),
        },
    )

    try:
        continuity_check_report = run_continuity_check_for_job(
            job=job,
            metadata={
                "stage": "2B-30-C",
                "job_id": getattr(job, "job_id", None),
            },
        )
        apply_continuity_check_run_report_to_job(
            job=job,
            report=continuity_check_report,
        )

        _continuity_check_details = {
            "status": continuity_check_report.status,
            "issue_count": continuity_check_report.issue_count,
            "blocking_issue_count": continuity_check_report.blocking_issue_count,
            "sentence_break_risk_count": (
                continuity_check_report.sentence_break_risk_count
            ),
            "context_jump_risk_count": (
                continuity_check_report.context_jump_risk_count
            ),
            "censor_context_risk_count": (
                continuity_check_report.censor_context_risk_count
            ),
            "timing_issue_count": continuity_check_report.timing_issue_count,
            "transition_conflict_count": (
                continuity_check_report.transition_conflict_count
            ),
            "technical_issue_count": continuity_check_report.technical_issue_count,
            "protected_context_count": continuity_check_report.protected_context_count,
            "recommendation": continuity_check_report.recommendation,
            "warnings": list(continuity_check_report.warnings or []),
            "errors": list(continuity_check_report.errors or []),
            "review_only": True,
        }

        _continuity_check_status_text = str(
            continuity_check_report.status or ""
        ).lower()

        if _continuity_check_status_text in {"ok", "completed_with_warnings"}:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="continuity_check",
                event_type="CONTINUITY_CHECK_DONE",
                action="continue_pipeline",
                status=(
                    "warn"
                    if _continuity_check_status_text == "completed_with_warnings"
                    else "ok"
                ),
                reason=continuity_check_report.recommendation
                or "continuity_check_completed",
                details=_continuity_check_details,
            )
        elif _continuity_check_status_text in {
            "skipped_no_transition_decisions",
            "skipped_no_cut_list_items",
        }:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="continuity_check",
                event_type="CONTINUITY_CHECK_SKIPPED",
                action="continue_pipeline",
                status="warn",
                reason=continuity_check_report.recommendation
                or "continuity_check_skipped_no_inputs",
                details=_continuity_check_details,
            )
        else:
            _safe_log_decision(
                job=job,
                export_dir=job_state_export_dir,
                phase="continuity_check",
                event_type="CONTINUITY_CHECK_FAILED",
                action="continue_pipeline",
                status="warn",
                reason=continuity_check_report.recommendation
                or "continuity_check_failed",
                details=_continuity_check_details,
            )

    except Exception as continuity_check_exc:
        job.continuity_check_status = "failed"
        job.continuity_check_recommendation = "continuity_check_failed"

        _safe_log_decision(
            job=job,
            export_dir=job_state_export_dir,
            phase="continuity_check",
            event_type="CONTINUITY_CHECK_FAILED",
            action="continue_pipeline",
            status="warn",
            reason="continuity_check_exception",
            details={"error": str(continuity_check_exc)},
        )

    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="continuity_check_done",
        reason="continuity_check_completed_or_skipped",
    )
    # -- End Continuity Check ---------------------------------------------------

    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="state",

        event_type="STATE_ANALYZING",
        action="transition_to_analyzing",
        reason="pipeline_analysis_started",
    )

    # JSON ProfileManager is the editable source of truth for channel profile values.
    # editing_profile_registry.resolve(...) stays temporarily for legacy mode/profile objects
    # until later phases migrate the remaining engines.
    
    _channel_str = getattr(
        getattr(job, "channel_type", None),
        "value",
        getattr(job, "channel", "gaming_main"),
    )
    _profile, _mode_config = resolve(
        channel_str=str(_channel_str or "gaming_main"),
        quality_mode_str=str(getattr(job, "quality_mode", "pro") or "pro"),
    )
    _editing_profile_log = (
        f"[gaming_pipeline] EDITING_PROFILE job={job.job_id} "
        f"channel={_profile.channel.value} "
        f"profile={_profile.channel.value} "
        f"content_family={_profile.content_family.value} "
        f"output_style={_profile.output_style.value} "
        f"quality_mode={_mode_config.mode.value} "
        f"analysis_depth={_mode_config.analysis_depth} "
        f"cut_aggressiveness={_profile.cut_aggressiveness}"
    )
    logger.info(_editing_profile_log)
    print(_editing_profile_log)

    transcript_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        ensure_ffmpeg_on_path()
        # Test-only bypass; do not set ZENITH_SKIP_TRANSCRIPT in production runs.
        if os.environ.get("ZENITH_SKIP_TRANSCRIPT") == "1":
            print(
                f"[gaming_pipeline] TRANSCRIPT {job.job_id} "
                "skipped reason=env skip (ZENITH_SKIP_TRANSCRIPT test-only bypass)"
            )
        elif job.raw_video_path:
            try:
                transcript_result = transcript_processor.transcribe(str(job.raw_video_path))
                print(
                    f"[gaming_pipeline] TRANSCRIPT {job.job_id} "
                    f"segments={len(transcript_result.segments)} "
                    f"engine={transcript_result.engine}"
                )
            except (TranscriptUnavailableError, ImportError, FileNotFoundError, RuntimeError) as exc:
                print(f"[gaming_pipeline] TRANSCRIPT {job.job_id} skipped reason={exc}")
        else:
            print(f"[gaming_pipeline] TRANSCRIPT {job.job_id} skipped reason=no raw_video_path")

    hook_keyword_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        hook_keyword_extractor = services.get("hook_keyword_extractor") or HookKeywordExtractor()

        if transcript_result is not None:
            hook_keyword_result = hook_keyword_extractor.analyze(transcript_result)
            print(
                f"[gaming_pipeline] HOOKS     {job.job_id} "
                f"hooks={len(hook_keyword_result.hook_sentences)} "
                f"keywords={len(hook_keyword_result.keywords)} "
                f"engine={hook_keyword_result.engine}"
            )
        else:
            print(f"[gaming_pipeline] HOOKS     {job.job_id} skipped reason=no transcript")

    sentence_timeline_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        if transcript_result is not None:
            sentence_timeline_result = SentenceTimelineBuilder().build(transcript_result)
            print(
                f"[gaming_pipeline] SENTENCES {job.job_id} "
                f"total={sentence_timeline_result.total_sentences} "
                f"hooks={sentence_timeline_result.hook_sentence_count} "
                f"fillers={sentence_timeline_result.filler_sentence_count} "
                f"incomplete={sentence_timeline_result.incomplete_sentence_count} "
                f"avg={sentence_timeline_result.average_score} "
                f"max={sentence_timeline_result.max_score} "
                f"engine={sentence_timeline_result.engine}"
            )
        else:
            print(f"[gaming_pipeline] SENTENCES {job.job_id} skipped reason=no transcript")

    # ------------------------------------------------------------------
    # Profile laden (channel-specific cut scoring)
    # ------------------------------------------------------------------
    channel_str = getattr(job.channel_type, "value", str(job.channel_type))
    target_str = (
        getattr(job.target_format, "value", str(job.target_format))
        if job.target_format else None
    )
    cut_profile = ChannelCutProfileProvider().get_profile(channel_str, target_str)
    print(
        f"[gaming_pipeline] CUT_PROFILE {job.job_id} "
        f"channel={channel_str} "
        f"profile={cut_profile.profile_name} "
        f"target_pacing={cut_profile.target_pacing} "
        f"min_seg={cut_profile.min_segment_duration_seconds} "
        f"max_seg={cut_profile.max_segment_duration_seconds}"
    )
    _top_weights = sorted(
        cut_profile.indicator_weights.items(),
        key=lambda kv: -abs(kv[1]),
    )[:8]
    if _top_weights:
        print(
            f"[gaming_pipeline] CUT_PROFILE_TOP {job.job_id} "
            + " ".join(f"{k}={v}" for k, v in _top_weights)
        )

    # ------------------------------------------------------------------
    # 1) Analyse + Edit-Entscheidung
    # ------------------------------------------------------------------
    analysis_result = analyzer.analyze(job)
    transition_job_state(
        job,
        JobStatus.ANALYZED,
        module="gaming_pipeline",
        reason="analysis_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="analyzed",
        reason="analysis_finished",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="analysis",
        event_type="ANALYSIS_DONE",
        action="analyzer_completed",
        reason="analysis_finished",
        details={
            "analysis_duration_seconds": getattr(analysis_result, "duration_seconds", None),
            "usable_for_longform": getattr(analysis_result, "usable_for_longform", None),
            "debug_context": debug_context,
        },
    )
    print(f"[gaming_pipeline] ANALYZE   {job.job_id}  done")

    transition_job_state(
        job,
        JobStatus.CUTTING,
        module="gaming_pipeline",
        reason="cutting_started",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="cutting",
        reason="cutting_started",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="cut",
        event_type="CUTTING_STARTED",
        action="transition_to_cutting",
        reason="cutting_started",
    )
    edit_decision = cutter.build_cut(job, analysis_result)
    transition_job_state(
        job,
        JobStatus.CUT,
        module="gaming_pipeline",
        reason="cutting_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="cut",
        reason="cutting_finished",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="cut",
        event_type="CUT_DONE",
        action="cut_builder_completed",
        reason="cutting_finished",
        details={
            "edit_decision_type": type(edit_decision).__name__,
            "debug_context": debug_context,
        },
    )
    print(f"[gaming_pipeline] CUT       {job.job_id}  done")

    # ------------------------------------------------------------------
    # 2) Edit-Signale
    # ------------------------------------------------------------------
    edit_signals = EditSignalExtractor().extract(job, analysis_result)
    print(f"[gaming_pipeline] SIGNALS   {job.job_id}  "
          f"signals={len(edit_signals)}")

    silence_zones = [
        signal for signal in edit_signals
        if signal.signal_type == "silence_zone"
    ]
    low_motion_zones = [
        signal for signal in edit_signals
        if signal.signal_type == "low_motion_zone"
    ]
    print(
        f"[gaming_pipeline] SILENCE   {job.job_id}  "
        f"silence_zones={len(silence_zones)} "
        f"low_motion_zones={len(low_motion_zones)}"
    )


    energy_curve_result = EnergyCurveBuilder().build(
        job_id=job.job_id,
        edit_signals=edit_signals,
        duration_seconds=getattr(
            analysis_result,
            "duration_seconds",
            getattr(job, "duration_seconds", None),
        ),
        window_seconds=5.0,
        max_peaks=5,
    )
    print(
        f"[gaming_pipeline] ENERGY   {job.job_id} "
        f"points={len(energy_curve_result.points)} "
        f"peaks={len(energy_curve_result.peak_points)} "
        f"avg={energy_curve_result.average_energy} "
        f"max={energy_curve_result.max_energy} "
        f"engine={energy_curve_result.engine}"
    )

    audio_role_result = AudioRoleIndicatorBuilder().build(
        edit_signals=edit_signals,
        transcript_result=transcript_result,
        sentence_timeline_result=sentence_timeline_result,
        energy_curve_result=energy_curve_result,
        channel_type=job.channel_type,
    )
    audio_role_counts = audio_role_result.role_counts
    print(
        f"[gaming_pipeline] AUDIO_ROLES {job.job_id} "
        f"total={len(audio_role_result.windows)} "
        f"speech={audio_role_counts.get('speech_active', 0)} "
        f"secondary={audio_role_counts.get('secondary_speech_like', 0)} "
        f"group={audio_role_counts.get('group_reaction_like', 0)} "
        f"laugh={audio_role_counts.get('laugh_like_audio', 0)} "
        f"shout={audio_role_counts.get('shout_like_audio', 0)} "
        f"game_peak={audio_role_counts.get('game_audio_peak', 0)} "
        f"silence={audio_role_counts.get('silence_or_dead_air', 0)} "
        f"risk={audio_role_counts.get('speech_cut_risk_audio', 0)} "
        f"engine={audio_role_result.engine}"
    )

    gameplay_vision_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        gameplay_vision_analyzer = services.get("gameplay_vision_analyzer") or GameplayVisionAnalyzer()

        if job.raw_video_path:
            gameplay_vision_result = gameplay_vision_analyzer.analyze_video(
                video_path=str(job.raw_video_path),
                max_frames=160,
            )

            if gameplay_vision_result.skipped_reason:
                print(
                    f"[gaming_pipeline] VISION   {job.job_id} "
                    f"skipped reason={gameplay_vision_result.skipped_reason}"
                )
            else:
                print(
                    f"[gaming_pipeline] VISION   {job.job_id} "
                    f"windows={len(gameplay_vision_result.windows)} "
                    f"action_windows={len(gameplay_vision_result.action_windows)} "
                    f"avg={gameplay_vision_result.average_action_score} "
                    f"max={gameplay_vision_result.max_action_score} "
                    f"engine={gameplay_vision_result.engine}"
                )
        else:
            gameplay_vision_result = gameplay_vision_analyzer.analyze_video(None)
            print(
                f"[gaming_pipeline] VISION   {job.job_id} "
                f"skipped reason={gameplay_vision_result.skipped_reason}"
            )
    gameplay_event_result = GameplayEventIndicatorBuilder().build(
        gameplay_vision_result=gameplay_vision_result,
        energy_curve_result=energy_curve_result,
        edit_signals=edit_signals,
        audio_role_result=audio_role_result,
        sentence_timeline_result=sentence_timeline_result,
        channel_type=job.channel_type,
    )
    gameplay_event_counts = gameplay_event_result.event_counts
    print(
        f"[gaming_pipeline] GAMEPLAY_EVENTS {job.job_id} "
        f"total={len(gameplay_event_result.windows)} "
        f"high_action={gameplay_event_counts.get('high_action_burst', 0)} "
        f"sustained={gameplay_event_counts.get('sustained_action', 0)} "
        f"flash={gameplay_event_counts.get('goal_or_save_like_flash', 0)} "
        f"round_dead={gameplay_event_counts.get('round_end_dead_time', 0)} "
        f"replay={gameplay_event_counts.get('replay_like_moment', 0)} "
        f"kickoff={gameplay_event_counts.get('kickoff_like', 0)} "
        f"idle="
        f"{gameplay_event_counts.get('menu_or_idle', 0) + gameplay_event_counts.get('low_gameplay_value', 0)} "
        f"engine={gameplay_event_result.engine}"
    )
    facecam_reaction_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        facecam_reaction_analyzer = services.get("facecam_reaction_analyzer") or FacecamReactionAnalyzer()

        if job.raw_video_path:
            facecam_reaction_result = facecam_reaction_analyzer.analyze_video(
                video_path=str(job.raw_video_path),
                sample_every_seconds=1.0,
                max_frames=160,
            )

            if facecam_reaction_result.skipped_reason:
                print(
                    f"[gaming_pipeline] FACECAM  {job.job_id} "
                    f"skipped reason={facecam_reaction_result.skipped_reason}"
                )
            else:
                print(
                    f"[gaming_pipeline] FACECAM  {job.job_id} "
                    f"windows={len(facecam_reaction_result.windows)} "
                    f"reactions={len(facecam_reaction_result.reaction_windows)} "
                    f"avg={facecam_reaction_result.average_reaction_score} "
                    f"max={facecam_reaction_result.max_reaction_score} "
                    f"engine={facecam_reaction_result.engine}"
                )
        else:
            facecam_reaction_result = facecam_reaction_analyzer.analyze_video(None)
            print(
                f"[gaming_pipeline] FACECAM  {job.job_id} "
                f"skipped reason={facecam_reaction_result.skipped_reason}"
            )

    facecam_emotion_result = FacecamEmotionIndicatorBuilder().build(
        facecam_reaction_result=facecam_reaction_result,
        audio_role_result=audio_role_result,
        sentence_timeline_result=sentence_timeline_result,
        gameplay_event_result=gameplay_event_result,
        channel_type="gaming_main",
    )
    facecam_emotion_counts = facecam_emotion_result.emotion_counts
    print(
        f"[gaming_pipeline] FACECAM_EMOTIONS {job.job_id} "
        f"total={len(facecam_emotion_result.windows)} "
        f"reaction={facecam_emotion_counts.get('facecam_reaction_spike', 0)} "
        f"motion={facecam_emotion_counts.get('facecam_motion_spike', 0)} "
        f"expression={facecam_emotion_counts.get('expression_change_like', 0)} "
        f"mouth={facecam_emotion_counts.get('mouth_open_like', 0)} "
        f"smile={facecam_emotion_counts.get('smile_like', 0)} "
        f"shock={facecam_emotion_counts.get('shock_like', 0)} "
        f"laugh={facecam_emotion_counts.get('laugh_like_face', 0)} "
        f"head={facecam_emotion_counts.get('head_movement_like', 0)} "
        f"thumbnail={facecam_emotion_counts.get('thumbnail_face_candidate', 0)} "
        f"low={facecam_emotion_counts.get('low_facecam_value', 0)} "
        f"engine={facecam_emotion_result.engine}"
    )

    round_phase_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        round_phase_result = RoundPhaseDetector().detect(
            job=job,
            analysis_result=analysis_result,
            edit_signals=edit_signals,
            audio_peaks=energy_curve_result.peak_points,
            transcript_result=transcript_result,
            gameplay_vision_result=gameplay_vision_result,
            facecam_reaction_result=facecam_reaction_result,
            gameplay_event_result=gameplay_event_result,
        )
        phase_counts = round_phase_result.phase_counts
        print(
            f"[gaming_pipeline] PHASES {job.job_id} "
            f"count={len(round_phase_result.windows)} "
            f"active={phase_counts.get(RoundPhase.ACTIVE_ROUND.value, 0)} "
            f"goals={phase_counts.get(RoundPhase.GOAL_REPLAY.value, 0)} "
            f"round_end={phase_counts.get(RoundPhase.ROUND_END.value, 0)} "
            f"menu_wait={phase_counts.get(RoundPhase.MENU_WAIT.value, 0)} "
            f"queue_wait={phase_counts.get(RoundPhase.QUEUE_WAIT.value, 0)} "
            f"countdown={phase_counts.get(RoundPhase.COUNTDOWN_KICKOFF.value, 0)} "
            f"engine={round_phase_result.engine}"
        )

    gameplay_state_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        gameplay_state_result = GameplayStateAnalyzer().analyze(
            video_path=job.raw_video_path,
            gameplay_vision_result=gameplay_vision_result,
            gameplay_event_result=gameplay_event_result,
            round_phase_result=round_phase_result,
        )
        state_counts = gameplay_state_result.state_counts
        print(
            f"[gaming_pipeline] GAMEPLAY_STATE {job.job_id} "
            f"total={gameplay_state_result.total_windows} "
            f"active={state_counts.get('active_gameplay', 0)} "
            f"menu_wait={state_counts.get('menu_wait', 0)} "
            f"round_end={state_counts.get('round_end', 0)} "
            f"replay={state_counts.get('replay_like', 0)} "
            f"low_wait={state_counts.get('low_motion_wait', 0)} "
            f"high_action={state_counts.get('high_motion_action', 0)} "
            f"pre_context={state_counts.get('possible_pre_action_context', 0)} "
            f"dead_after_goal={state_counts.get('possible_dead_time_after_goal', 0)} "
            f"engine={gameplay_state_result.engine}"
        )

    # ------------------------------------------------------------------
    # 3) Highlight-Selektion
    # ------------------------------------------------------------------
    highlight_result = HighlightSelector().select(
        job,
        analysis_result,
        edit_signals,
    )
    print(f"[gaming_pipeline] HIGHLIGHTS {job.job_id}  "
          f"candidates={len(highlight_result.get('highlight_candidates', []))}")

    cut_indicator_result = CutIndicatorBuilder().build(
        edit_signals=edit_signals,
        transcript_result=transcript_result,
        sentence_timeline_result=sentence_timeline_result,
        audio_role_result=audio_role_result,
        gameplay_event_result=gameplay_event_result,
        energy_curve_result=energy_curve_result,
        gameplay_vision_result=gameplay_vision_result,
        facecam_reaction_result=facecam_reaction_result,
        facecam_emotion_result=facecam_emotion_result,
        edit_timeline=None,
        channel_type=job.channel_type,
    )
    print(
        f"[gaming_pipeline] INDICATORS {job.job_id} "
        f"total={len(cut_indicator_result.indicators)} "
        f"positive={cut_indicator_result.positive_count} "
        f"negative={cut_indicator_result.negative_count} "
        f"neutral={cut_indicator_result.neutral_count} "
        f"avg={cut_indicator_result.average_score} "
        f"max={cut_indicator_result.max_score} "
        f"engine={cut_indicator_result.engine}"
    )
    indicator_type_counts: dict[str, int] = {}
    for indicator in cut_indicator_result.indicators:
        indicator_type_counts[indicator.indicator_type] = (
            indicator_type_counts.get(indicator.indicator_type, 0) + 1
        )
    if indicator_type_counts:
        top_items = sorted(
            indicator_type_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:8]
        print(
            f"[gaming_pipeline] INDICATOR_TOP {job.job_id} "
            + " ".join(f"{name}={count}" for name, count in top_items)
        )

    universal_moment_result = UniversalMomentBrain().analyze(
        duration_seconds=getattr(
            analysis_result,
            "duration_seconds",
            getattr(job, "duration_seconds", None),
        ),
        transcript_result=transcript_result,
        sentence_timeline_result=sentence_timeline_result,
        audio_role_result=audio_role_result,
        gameplay_vision_result=gameplay_vision_result,
        gameplay_event_result=gameplay_event_result,
        gameplay_state_result=gameplay_state_result,
        facecam_reaction_result=facecam_reaction_result,
        facecam_emotion_result=facecam_emotion_result,
        cut_indicator_result=cut_indicator_result,
        round_phase_result=round_phase_result,
    )
    print(
        f"[gaming_pipeline] UNIVERSAL_MOMENTS {job.job_id} "
        f"windows={universal_moment_result.total_windows} "
        f"keep={universal_moment_result.keep_windows} "
        f"remove={universal_moment_result.remove_windows} "
        f"cut_risk={universal_moment_result.cut_risk_windows} "
        f"zoom_risk={universal_moment_result.zoom_risk_windows} "
        f"avg={universal_moment_result.avg_moment_score} "
        f"max={universal_moment_result.max_moment_score} "
        f"engine={universal_moment_result.engine}"
    )

    filtered_highlights, phase_filter_stats = _filter_highlights_by_round_phase(
        highlight_result["highlight_candidates"],
        round_phase_result,
        cut_indicator_result,
        transcript_result,
    )
    highlight_result["highlight_candidates"] = filtered_highlights
    print(
        "[PHASE-FILTER] "
        f"dropped {phase_filter_stats['dropped']} highlights in menu_wait/queue_wait, "
        f"kept {phase_filter_stats['kept_override']} with hook/peak override"
    )
    print(
        f"[gaming_pipeline] PHASE_FILTER {job.job_id} "
        f"dropped={phase_filter_stats['dropped']} "
        f"kept_override={phase_filter_stats['kept_override']} "
        f"remaining={len(filtered_highlights)}"
    )

    # ------------------------------------------------------------------
    # 4) Longform-Timeline  (nur wenn Voraussetzungen erfÃ¼llt)
    # ------------------------------------------------------------------
    edit_timeline = None
    _fusion_timeline_note = None
    if (
        job.target_format == TargetFormat.LONGFORM
        and analysis_result.usable_for_longform
        and highlight_result["highlight_candidates"]
    ):
        edit_timeline = LongformTimelineBuilder().build(
            job=job,
            analysis_result=analysis_result,
            highlight_candidates=highlight_result["highlight_candidates"],
            weak_zones=highlight_result["weak_zones"],
            energy_curve_result=energy_curve_result,
            gameplay_vision_result=gameplay_vision_result,
            facecam_reaction_result=facecam_reaction_result,
            transcript_result=transcript_result,
            cut_indicator_result=cut_indicator_result,
            cut_scoring_profile=cut_profile,
            sentence_timeline_result=sentence_timeline_result,
            audio_role_result=audio_role_result,
            round_phase_result=round_phase_result,
            gameplay_state_result=gameplay_state_result,
            universal_moment_result=universal_moment_result,
        )
        _timeline_notes = getattr(edit_timeline, "timeline_notes", []) or []
        _fusion_timeline_note = next(
            (n for n in _timeline_notes if n.startswith("Indicator fusion:")),
            None,
        )
        if _fusion_timeline_note:
            print(
                f"[gaming_pipeline] INDICATOR_FUSION {job.job_id} "
                + _fusion_timeline_note[len("Indicator fusion: "):]
            )
        print(f"[gaming_pipeline] TIMELINE  {job.job_id}  "
              f"segments={len(edit_timeline.selected_segments)}  "
              f"score={edit_timeline.timeline_score}")
        boundary_counts = {
            "adjusted_start": sum(
                any(note.startswith("boundary_adjusted_start=") for note in segment.notes)
                for segment in edit_timeline.selected_segments
            ),
            "adjusted_end": sum(
                any(note.startswith("boundary_adjusted_end=") for note in segment.notes)
                for segment in edit_timeline.selected_segments
            ),
            "skipped": sum(
                any(note.startswith("boundary_skipped") for note in segment.notes)
                for segment in edit_timeline.selected_segments
            ),
        }
        print(
            f"[gaming_pipeline] BOUNDARY  {job.job_id} "
            f"adjusted_start={boundary_counts['adjusted_start']} "
            f"adjusted_end={boundary_counts['adjusted_end']} "
            f"skipped={boundary_counts['skipped']}"
        )
        cut_safety_counts = {
            "adjusted_start": sum(
                any(note.startswith("final_cut_safety_start=") for note in segment.notes)
                for segment in edit_timeline.selected_segments
            ),
            "adjusted_end": sum(
                any(
                    note.startswith("final_cut_safety_end=")
                    or note.startswith("final_cut_safety_end_fallback=")
                    for note in segment.notes
                )
                for segment in edit_timeline.selected_segments
            ),
            "skipped_start": sum(
                "final_cut_safety_start_skipped" in segment.notes
                for segment in edit_timeline.selected_segments
            ),
            "skipped_end": sum(
                "final_cut_safety_end_skipped" in segment.notes
                or any(note.startswith("final_cut_safety_end_fallback=") for note in segment.notes)
                for segment in edit_timeline.selected_segments
            ),
        }
        print(
            f"[gaming_pipeline] CUT_SAFETY {job.job_id} "
            f"adjusted_start={cut_safety_counts['adjusted_start']} "
            f"adjusted_end={cut_safety_counts['adjusted_end']} "
            f"skipped_start={cut_safety_counts['skipped_start']} "
            f"skipped_end={cut_safety_counts['skipped_end']}"
        )
        quality_note = next(
            (
                note for note in _timeline_notes
                if note.startswith("Final quality guard:")
            ),
            "",
        )

        def _quality_note_int(key: str) -> int:
            prefix = f"{key}="
            for part in quality_note.split():
                if part.startswith(prefix):
                    try:
                        return int(part.split("=", 1)[1])
                    except ValueError:
                        return 0
            return 0

        quality_counts = {
            "micro_removed": _quality_note_int("micro_removed"),
            "peak_micro_allowed": _quality_note_int("peak_micro_allowed"),
            "speech_start_adjusted": _quality_note_int("speech_start_adjusted"),
            "speech_end_adjusted": _quality_note_int("speech_end_adjusted"),
            "silence_edge_trimmed": _quality_note_int("silence_edge_trimmed"),
        }
        print(
            f"[gaming_pipeline] QUALITY_GUARD {job.job_id} "
            f"micro_removed={quality_counts['micro_removed']} "
            f"peak_micro_allowed={quality_counts['peak_micro_allowed']} "
            f"speech_adjusted="
            f"{quality_counts['speech_start_adjusted'] + quality_counts['speech_end_adjusted']} "
            f"silence_edge_trimmed={quality_counts['silence_edge_trimmed']}"
        )
        boost_counts = {
            "energy": sum("energy_boost" in segment.notes for segment in edit_timeline.selected_segments),
            "vision": sum("vision_boost" in segment.notes for segment in edit_timeline.selected_segments),
            "facecam": sum("facecam_boost" in segment.notes for segment in edit_timeline.selected_segments),
        }
        print(
            f"[gaming_pipeline] SCORING_BOOSTS {job.job_id} "
            f"energy={boost_counts['energy']} "
            f"vision={boost_counts['vision']} "
            f"facecam={boost_counts['facecam']}"
        )

        _seam_note = next(
            (n for n in _timeline_notes if n.startswith("Seam guard:")),
            "",
        )

        def _seam_int(key: str) -> int:
            prefix = f"{key}="
            for part in _seam_note.split():
                if part.startswith(prefix):
                    try:
                        return int(part.split("=", 1)[1])
                    except ValueError:
                        return 0
            return 0

        print(
            f"[gaming_pipeline] SEAM_GUARD {job.job_id} "
            f"mini_fixed={_seam_int('mini_fixed')} "
            f"speech_adjusted={_seam_int('speech_adjusted')} "
            f"speech_end_trimmed_back={_seam_int('speech_end_trimmed_back')} "
            f"reaction_context={_seam_int('reaction_context')} "
            f"secondary_speech={_seam_int('secondary_speech')} "
            f"speech_end_locked={_seam_int('speech_end_locked')} "
            f"shout_end_locked={_seam_int('shout_end_locked')} "
            f"phrase_end_locked={_seam_int('phrase_end_locked')} "
            f"seam_state_protected={_seam_int('seam_state_protected')} "
            f"low_value_removed={_seam_int('low_value_removed')} "
            f"menu_dead_time_removed={_seam_int('menu_dead_time_removed')}"
        )

        _round_wait_note = next(
            (n for n in _timeline_notes if n.startswith("Round wait guard:")),
            "",
        )
        _pre_action_note = next(
            (n for n in _timeline_notes if n.startswith("Pre action context:")),
            "",
        )
        _hard_speech_note = next(
            (n for n in _timeline_notes if n.startswith("Hard speech lock:")),
            "",
        )
        _pacing_note = next(
            (n for n in _timeline_notes if n.startswith("Pacing guard:")),
            "",
        )
        _private_menu_note = next(
            (n for n in _timeline_notes if n.startswith("Private menu speech:")),
            "",
        )
        _sentence_atomicity_note = next(
            (n for n in _timeline_notes if n.startswith("Sentence atomicity:")),
            "",
        )

        def _note_int(note: str, key: str) -> int:
            prefix = f"{key}="
            for part in note.split():
                if part.startswith(prefix):
                    try:
                        return int(part.split("=", 1)[1])
                    except ValueError:
                        return 0
            return 0

        print(
            f"[gaming_pipeline] ROUND_WAIT {job.job_id} "
            f"removed={_note_int(_round_wait_note, 'removed')} "
            f"trimmed={_note_int(_round_wait_note, 'trimmed')} "
            f"after_goal_tail_trimmed={_note_int(_round_wait_note, 'after_goal_tail_trimmed')} "
            f"menu_speech_ignored={_note_int(_round_wait_note, 'menu_speech_ignored')} "
            f"kept_action={_note_int(_round_wait_note, 'kept_action')} "
            f"kept_speech={_note_int(_round_wait_note, 'kept_speech')} "
            f"gameplay_state_removed={_note_int(_round_wait_note, 'gameplay_state_removed')} "
            f"gameplay_state_trimmed={_note_int(_round_wait_note, 'gameplay_state_trimmed')} "
            f"protected_by_action_state={_note_int(_round_wait_note, 'protected_by_action_state')}"
        )
        print(
            f"[gaming_pipeline] PRE_ACTION_CONTEXT {job.job_id} "
            f"expanded={_note_int(_pre_action_note, 'expanded')} "
            f"shout={_note_int(_pre_action_note, 'shout')} "
            f"goal={_note_int(_pre_action_note, 'goal')} "
            f"action={_note_int(_pre_action_note, 'action')} "
            f"strong_action_context={_note_int(_pre_action_note, 'strong_action_context')} "
            f"smart_backfilled={_note_int(_pre_action_note, 'smart_backfilled')} "
            f"silence_stop={_note_int(_pre_action_note, 'silence_stop')} "
            f"boundary_stop={_note_int(_pre_action_note, 'boundary_stop')} "
            f"phase_stop={_note_int(_pre_action_note, 'phase_stop')} "
            f"skipped_overlap={_note_int(_pre_action_note, 'skipped_overlap')} "
            f"skipped_silence={_note_int(_pre_action_note, 'skipped_silence')} "
            f"gameplay_state_backfilled={_note_int(_pre_action_note, 'gameplay_state_backfilled')} "
            f"goal_state_backfilled={_note_int(_pre_action_note, 'goal_state_backfilled')} "
            f"action_state_backfilled={_note_int(_pre_action_note, 'action_state_backfilled')}"
        )
        print(
            f"[gaming_pipeline] HARD_SPEECH_LOCK {job.job_id} "
            f"word_locked={_note_int(_hard_speech_note, 'word_locked')} "
            f"sentence_locked={_note_int(_hard_speech_note, 'sentence_locked')} "
            f"phrase_locked={_note_int(_hard_speech_note, 'phrase_locked')} "
            f"shout_locked={_note_int(_hard_speech_note, 'shout_locked')} "
            f"secondary_locked={_note_int(_hard_speech_note, 'secondary_locked')} "
            f"micro_fixed={_note_int(_hard_speech_note, 'micro_fixed')} "
            f"short_removed={_note_int(_hard_speech_note, 'short_useless_removed')}"
        )
        print(
            f"[gaming_pipeline] PACING_GUARD {job.job_id} "
            f"micro_fixed={_note_int(_pacing_note, 'micro_fixed')} "
            f"boring_removed={_note_int(_pacing_note, 'boring_wait_removed')} "
            f"boring_trimmed={_note_int(_pacing_note, 'boring_wait_trimmed')} "
            f"neutral_speech_ignored={_note_int(_pacing_note, 'neutral_speech_ignored')} "
            f"round_start_trimmed={_note_int(_pacing_note, 'round_start_wait_trimmed')} "
            f"round_end_expanded={_note_int(_pacing_note, 'round_end_context_expanded')} "
            f"action_expanded={_note_int(_pacing_note, 'action_context_expanded')}"
        )
        print(
            f"[gaming_pipeline] PRIVATE_MENU_SPEECH {job.job_id} "
            f"removed={_note_int(_private_menu_note, 'removed')} "
            f"trimmed={_note_int(_private_menu_note, 'trimmed')} "
            f"round_start_shifted={_note_int(_private_menu_note, 'round_start_shifted')} "
            f"menu_sentences_removed={_note_int(_private_menu_note, 'menu_sentences_removed')} "
            f"active_speech_kept={_note_int(_private_menu_note, 'active_speech_kept')}"
        )
        print(
            f"[gaming_pipeline] SENTENCE_ATOMICITY {job.job_id} "
            f"sentence_fixed="
            f"{_note_int(_sentence_atomicity_note, 'sentence_start_fixed') + _note_int(_sentence_atomicity_note, 'sentence_end_fixed')} "
            f"partial_removed={_note_int(_sentence_atomicity_note, 'sentence_partial_removed')} "
            f"partial_kept_budget={_note_int(_sentence_atomicity_note, 'partial_kept_budget')} "
            f"first_context_kept={_note_int(_sentence_atomicity_note, 'first_context_kept')} "
            f"budget_restored={_note_int(_sentence_atomicity_note, 'budget_restored')} "
            f"secondary_fixed={_note_int(_sentence_atomicity_note, 'secondary_sentence_fixed')} "
            f"micro_removed={_note_int(_sentence_atomicity_note, 'micro_segments_removed')} "
            f"action_lead_trimmed={_note_int(_sentence_atomicity_note, 'action_lead_trimmed')} "
            f"round_action_protected={_note_int(_sentence_atomicity_note, 'round_start_action_protected')}"
        )

        _round_lifecycle_note = next(
            (n for n in _timeline_notes if n.startswith("Round lifecycle:")),
            "",
        )
        _universal_assist_note = next(
            (n for n in _timeline_notes if n.startswith("Universal moment assist:")),
            "",
        )
        print(
            f"[gaming_pipeline] ROUND_LIFECYCLE {job.job_id} "
            f"menu_removed={_note_int(_round_lifecycle_note, 'menu_removed')} "
            f"round_start_shifted={_note_int(_round_lifecycle_note, 'round_start_shifted')} "
            f"pre_goal_expanded={_note_int(_round_lifecycle_note, 'pre_goal_expanded')} "
            f"post_goal_extended={_note_int(_round_lifecycle_note, 'post_goal_extended')} "
            f"boring_removed={_note_int(_round_lifecycle_note, 'boring_removed')} "
            f"boring_trimmed={_note_int(_round_lifecycle_note, 'boring_trimmed')}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_ASSIST {job.job_id} "
            f"keep={_note_int(_universal_assist_note, 'keep_protected')} "
            f"remove_supported={_note_int(_universal_assist_note, 'remove_supported')} "
            f"pre={_note_int(_universal_assist_note, 'pre_context_protected')} "
            f"post={_note_int(_universal_assist_note, 'post_context_protected')} "
            f"cut_risk={_note_int(_universal_assist_note, 'cut_risk_protected')} "
            f"zoom_risk={_note_int(_universal_assist_note, 'zoom_risk_marked')} "
            f"private={_note_int(_universal_assist_note, 'private_menu_supported')}"
        )
        universal_moment_debug_report = UniversalMomentDebugReporter().build(
            job_id=job.job_id,
            timeline_segments=edit_timeline.selected_segments,
            universal_moment_result=universal_moment_result,
        )
        universal_moment_debug_paths = _write_universal_debug_report(
            job,
            universal_moment_debug_report,
        )
        universal_moment_soft_decision_report = UniversalMomentSoftDecisionBuilder().build(
            job_id=job.job_id,
            debug_report=universal_moment_debug_report,
        )
        universal_moment_soft_decision_paths = _write_universal_soft_decision_report(
            job,
            universal_moment_soft_decision_report,
        )
        universal_role_decision_audit_report = UniversalRoleDecisionAuditor().build(
            job_id=job.job_id,
            debug_report=universal_moment_debug_report,
            soft_decision_report=universal_moment_soft_decision_report,
        )
        universal_role_decision_audit_paths = _write_universal_role_decision_audit_report(
            job,
            universal_role_decision_audit_report,
        )
        universal_context_audit_report = UniversalContextAuditor().build(
            job_id=job.job_id,
            timeline_segments=edit_timeline.selected_segments,
            debug_report=universal_moment_debug_report,
            soft_decision_report=universal_moment_soft_decision_report,
            role_decision_audit_report=universal_role_decision_audit_report,
            universal_moment_result=universal_moment_result,
        )
        universal_context_audit_paths = _write_universal_context_audit_report(
            job,
            universal_context_audit_report,
        )
        universal_boundary_evidence_report = UniversalBoundaryEvidenceReporter().build(
            job_id=job.job_id,
            timeline_segments=edit_timeline.selected_segments,
            transcript_result=transcript_result,
            sentence_timeline_result=sentence_timeline_result,
            audio_role_result=audio_role_result,
            universal_moment_result=universal_moment_result,
            context_audit_report=universal_context_audit_report,
            final_review_report=None,
        )
        universal_boundary_evidence_paths = _write_universal_boundary_evidence_report(
            job,
            universal_boundary_evidence_report,
        )
        phase_2b_final_review_report = Phase2BFinalReviewBuilder().build(
            job_id=job.job_id,
            debug_report=universal_moment_debug_report,
            soft_decision_report=universal_moment_soft_decision_report,
            role_decision_audit_report=universal_role_decision_audit_report,
            context_audit_report=universal_context_audit_report,
            boundary_evidence_report=universal_boundary_evidence_report,
        )
        phase_2b_final_review_paths = _write_phase_2b_final_review_report(
            job,
            phase_2b_final_review_report,
        )
        universal_moment_review_paths = _write_universal_review_report(
            job,
            universal_moment_debug_report,
            soft_decision_report=universal_moment_soft_decision_report,
            role_decision_audit_report=universal_role_decision_audit_report,
            context_audit_report=universal_context_audit_report,
            boundary_evidence_report=universal_boundary_evidence_report,
            final_review_report=phase_2b_final_review_report,
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_DEBUG {job.job_id} "
            f"segments={universal_moment_debug_report.total_segments} "
            f"keep={universal_moment_debug_report.segments_with_keep_signal} "
            f"remove={universal_moment_debug_report.segments_with_remove_signal} "
            f"cut_risk={universal_moment_debug_report.segments_with_cut_risk} "
            f"zoom_risk={universal_moment_debug_report.segments_with_zoom_risk} "
            f"private={universal_moment_debug_report.segments_with_private_risk} "
            f"avg={universal_moment_debug_report.avg_segment_moment_score}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_SOFT_DECISION {job.job_id} "
            f"segments={universal_moment_soft_decision_report.total_segments} "
            f"safe_keep={universal_moment_soft_decision_report.safe_keep} "
            f"keep={universal_moment_soft_decision_report.keep_dominant} "
            f"trim={universal_moment_soft_decision_report.trim_edges_candidate} "
            f"remove={universal_moment_soft_decision_report.remove_dominant} "
            f"review={universal_moment_soft_decision_report.needs_human_review} "
            f"avg_conflict={universal_moment_soft_decision_report.avg_conflict_score}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_ROLE_AUDIT {job.job_id} "
            f"segments={universal_role_decision_audit_report.total_segments} "
            f"protected_trim_conflicts={universal_role_decision_audit_report.protected_trim_conflicts} "
            f"review_maybe_trim={universal_role_decision_audit_report.review_maybe_trim} "
            f"safe_keep_correct={universal_role_decision_audit_report.safe_keep_correct} "
            f"aligned={universal_role_decision_audit_report.aligned} "
            f"unclear={universal_role_decision_audit_report.unclear}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_CONTEXT_AUDIT {job.job_id} "
            f"segments={universal_context_audit_report.total_segments} "
            f"setup={universal_context_audit_report.keep_as_setup} "
            f"payoff={universal_context_audit_report.keep_as_payoff} "
            f"chain={universal_context_audit_report.keep_context_chain} "
            f"private_block={universal_context_audit_report.private_menu_block_candidate} "
            f"boring_bridge={universal_context_audit_report.boring_bridge_candidate} "
            f"boundary={universal_context_audit_report.boundary_protect} "
            f"edge_trim={universal_context_audit_report.edge_trim_candidate} "
            f"review={universal_context_audit_report.needs_human_review} "
            f"avg_conflict={universal_context_audit_report.avg_context_conflict_score}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_BOUNDARY_EVIDENCE {job.job_id} "
            f"boundaries={universal_boundary_evidence_report.total_boundaries} "
            f"high={universal_boundary_evidence_report.real_high} "
            f"medium={universal_boundary_evidence_report.medium} "
            f"low={universal_boundary_evidence_report.low} "
            f"false_positive={universal_boundary_evidence_report.false_positive} "
            f"clean={universal_boundary_evidence_report.clean} "
            f"speech_real={universal_boundary_evidence_report.real_speech_cut_risk} "
            f"speech_possible={universal_boundary_evidence_report.possible_speech_cut_risk} "
            f"action={universal_boundary_evidence_report.action_cut_risk} "
            f"zoom={universal_boundary_evidence_report.zoom_cut_risk} "
            f"avg={universal_boundary_evidence_report.avg_boundary_risk_score}"
        )
        print(
            f"[gaming_pipeline] UNIVERSAL_BOUNDARY_CALIBRATION {job.job_id} "
            f"real_word={universal_boundary_evidence_report.real_word_cut} "
            f"real_sentence={universal_boundary_evidence_report.real_sentence_cut} "
            f"likely={universal_boundary_evidence_report.likely_speech_cut} "
            f"uncertain={universal_boundary_evidence_report.timestamp_uncertain} "
            f"audio_only={universal_boundary_evidence_report.audio_only_near_edge} "
            f"weak={universal_boundary_evidence_report.weak_speech_evidence} "
            f"safe={universal_boundary_evidence_report.probably_safe} "
            f"downgrade={universal_boundary_evidence_report.downgrade_candidates}"
        )
        print(
            f"[gaming_pipeline] PHASE_2B_FINAL_REVIEW {job.job_id} "
            f"segments={phase_2b_final_review_report.total_segments} "
            f"strong_keep={phase_2b_final_review_report.strong_keep} "
            f"boundary_warning={phase_2b_final_review_report.keep_with_boundary_warning} "
            f"review={phase_2b_final_review_report.review_needed} "
            f"edge_trim={phase_2b_final_review_report.possible_edge_trim_later} "
            f"safe={phase_2b_final_review_report.safe} "
            f"high={phase_2b_final_review_report.high_priority_reviews} "
            f"medium={phase_2b_final_review_report.medium_priority_reviews}"
        )
        if universal_moment_debug_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_DEBUG_FILE {job.job_id} "
                f"path={universal_moment_debug_paths[-1]}"
            )
        if universal_moment_soft_decision_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_SOFT_DECISION_FILE {job.job_id} "
                f"path={universal_moment_soft_decision_paths[-1]}"
            )
        if universal_role_decision_audit_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_ROLE_AUDIT_FILE {job.job_id} "
                f"path={universal_role_decision_audit_paths[-1]}"
            )
        if universal_context_audit_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_CONTEXT_AUDIT_FILE {job.job_id} "
                f"path={universal_context_audit_paths[-1]}"
            )
        if universal_boundary_evidence_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_BOUNDARY_EVIDENCE_FILE {job.job_id} "
                f"path={universal_boundary_evidence_paths[-1]}"
            )
        if phase_2b_final_review_paths:
            print(
                f"[gaming_pipeline] PHASE_2B_FINAL_REVIEW_FILE {job.job_id} "
                f"path={phase_2b_final_review_paths[-1]}"
            )
        if universal_moment_review_paths:
            print(
                f"[gaming_pipeline] UNIVERSAL_REVIEW {job.job_id} "
                f"file={universal_moment_review_paths[-1]}"
            )

        _safe_trim_segments, _safe_trim_summary = UniversalSafeEdgeTrimApplier().apply(
            edit_timeline.selected_segments,
            universal_moment_result=universal_moment_result,
            soft_decision_report=universal_moment_soft_decision_report,
        )
        edit_timeline.selected_segments = _safe_trim_segments
        print(
            f"[gaming_pipeline] UNIVERSAL_SAFE_TRIM {job.job_id} "
            f"candidates={_safe_trim_summary.trim_candidates_seen} "
            f"start={_safe_trim_summary.start_trimmed} "
            f"end={_safe_trim_summary.end_trimmed} "
            f"trimmed_seconds={_safe_trim_summary.total_trimmed_seconds:.3f}"
        )

    # ------------------------------------------------------------------
    # 5) Reframe-Plan
    # ------------------------------------------------------------------
    reframe_plan = None
    if edit_timeline is not None:
        reframe_plan = ReframingCore().build_plan(
            job=job,
            timeline=edit_timeline,
            highlight_candidates=highlight_result["highlight_candidates"],
            source_aspect_ratio="32:9",
            primary_target_aspect_ratio="16:9",
            secondary_target_aspect_ratio="9:16",
        )
        facecam_guard_summary = FacecamIntroGuard().apply(
            timeline=edit_timeline,
            reframe_plan=reframe_plan,
            facecam_reaction_result=facecam_reaction_result,
        )
        print(
            f"[gaming_pipeline] FACECAM_GUARD {job.job_id} "
            f"converted={facecam_guard_summary.converted} "
            f"intro_blocked={facecam_guard_summary.intro_blocked} "
            f"limited={facecam_guard_summary.limited} "
            f"no_reaction_blocked={facecam_guard_summary.no_reaction_blocked} "
            f"allowed_short_reactions={facecam_guard_summary.allowed_short_reactions}"
        )
        if facecam_guard_summary.examples:
            print(
                f"[gaming_pipeline] FACECAM_GUARD_EXAMPLES {job.job_id} "
                f"{'; '.join(facecam_guard_summary.examples)}"
            )
        print(f"[gaming_pipeline] REFRAME   {job.job_id}  "
              f"instructions={len(reframe_plan.instructions)}")

    # ------------------------------------------------------------------
    # 6) Reaction-Momente + Zoom-Plan
    # ------------------------------------------------------------------
    dynamic_edit_plan = None
    if edit_timeline is not None and reframe_plan is not None:
        reaction_moments = ReactionMomentDetector().detect(
            job=job,
            timeline=edit_timeline,
            edit_signals=edit_signals,
            reframe_plan=reframe_plan,
        )

        dynamic_edit_plan = ZoomPacingEngine().build_plan(
            job=job,
            timeline=edit_timeline,
            reframe_plan=reframe_plan,
            reaction_moments=reaction_moments,
        )

        zoom_smooth_summary = FacecamZoomSmoothnessGuard().apply(
            edit_timeline,
            dynamic_edit_plan,
            facecam_reaction_result=facecam_reaction_result,
            audio_role_result=audio_role_result,
            cut_indicator_result=cut_indicator_result,
            reframe_plan=reframe_plan,
            gameplay_state_result=gameplay_state_result,
        )
        print(
            f"[gaming_pipeline] FACECAM_ZOOM_SMOOTHNESS {job.job_id} "
            f"removed={zoom_smooth_summary.removed} "
            f"shifted={zoom_smooth_summary.shifted} "
            f"edge_blocked={zoom_smooth_summary.edge_blocked} "
            f"short_removed={zoom_smooth_summary.short_removed} "
            f"weak_reaction_removed={zoom_smooth_summary.weak_reaction_removed} "
            f"silence_removed={zoom_smooth_summary.silence_removed} "
            f"tail_trimmed={zoom_smooth_summary.tail_trimmed} "
            f"state_zoom_removed={zoom_smooth_summary.state_zoom_removed} "
            f"state_zoom_trimmed={zoom_smooth_summary.state_zoom_trimmed} "
            f"state_zoom_protected={zoom_smooth_summary.state_zoom_protected}"
        )

        print(f"[gaming_pipeline] ZOOM      {job.job_id}  "
              f"zoom_instructions={len(dynamic_edit_plan.zoom_instructions)}")

        if dynamic_edit_plan.zoom_instructions:
            print(f"\n[DEBUG] ========== ZOOM DEBUG ==========")
            for i, zoom in enumerate(dynamic_edit_plan.zoom_instructions):
                print(
                    f"[DEBUG]   Zoom {i+1}: "
                    f"seg={zoom.segment_id[:8]}, "
                    f"time={zoom.start_time:.1f}s-{zoom.end_time:.1f}s, "
                    f"intensity={zoom.intensity:.2f}"
                )
            print(f"[DEBUG] =====================================\n")

    # ------------------------------------------------------------------
    # 7) Render - FinalRenderDriver wenn Timeline vorhanden,
    #             sonst RenderProcessor als Fallback
    # ------------------------------------------------------------------
    if edit_timeline is not None and job.raw_video_path:
        _src = job.raw_video_path
        _tl  = edit_timeline
        _rf  = reframe_plan
        _dep = dynamic_edit_plan

        class _Adapter:
            def render(self, _job, _edit_decision, **_kw):
                return FinalRenderDriver().render(
                    job=_job,
                    source_path=_src,
                    edit_timeline=_tl,
                    reframe_plan=_rf,
                    dynamic_edit_plan=_dep,
                )

        active_renderer = _Adapter()
    else:
        active_renderer = renderer

    transition_job_state(
        job,
        JobStatus.RENDERING,
        module="gaming_pipeline",
        reason="rendering_started",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="rendering",
        reason="rendering_started",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="render",
        event_type="RENDERING_STARTED",
        action="renderer_started",
        reason="rendering_started",
        details={
            "renderer_type": type(active_renderer).__name__,
        },
    )
    final_video_path = active_renderer.render(job, edit_decision)
    transition_job_state(
        job,
        JobStatus.RENDERED,
        module="gaming_pipeline",
        reason="rendering_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=job_state_store,
        export_dir=job_state_export_dir,
        step_name="rendered",
        reason="rendering_finished",
    )
    _safe_log_decision(
        job=job,
        export_dir=job_state_export_dir,
        phase="render",
        event_type="RENDER_DONE",
        action="renderer_completed",
        reason="rendering_finished",
        details={
            "final_video_path": str(final_video_path),
            "debug_context": debug_context,
        },
    )
    print(f"[gaming_pipeline] RENDER    {job.job_id}  â†’ {final_video_path}")

    # ------------------------------------------------------------------
    # 8) Untertitel
    # ------------------------------------------------------------------
    subtitles = subtitle_processor.generate(job, edit_decision)
    print(f"[gaming_pipeline] SUBTITLES {job.job_id}  done")

    # ------------------------------------------------------------------
    # 9) Titel + Metadaten
    # ------------------------------------------------------------------
    title_package = title_gen.generate(job)
    metadata      = metadata_gen.generate(job, title_package)
    print(f"[gaming_pipeline] META      {job.job_id}  "
          f"title='{getattr(title_package, 'primary_title', '')[:40]}'")

    # ------------------------------------------------------------------
    # 10) Validator  (kein Thumbnail â†’ None)
    # ------------------------------------------------------------------
    validator_result = validator.validate(
        job,
        final_video_path,
        title_package,
        metadata,
        None,   # thumbnail_package - wird in Phase 2.5 gebaut
    )
    print(f"[gaming_pipeline] VALIDATE  {job.job_id}  "
          f"status={getattr(validator_result, 'validator_status', '-')}")
    _validator_reason = getattr(validator_result, "reason", "")
    if not _validator_reason:
        _blocking_issues = getattr(validator_result, "blocking_issues", []) or []
        _validator_reason = "; ".join(str(issue) for issue in _blocking_issues) or "not provided"
    print(
        f"[gaming_pipeline] VALIDATE_DETAIL {job.job_id} "
        f"status={getattr(validator_result, 'validator_status', '-')} "
        f"reason={_compact_log_value(_validator_reason)}"
    )

    channel_type = getattr(job.channel_type, "value", job.channel_type)
    export_dir = os.path.join("exports", str(channel_type), job.job_id)
    phase_2b_stabilization_result = Phase2BStabilizationChecker().check(
        job_id=job.job_id,
        job_dir="output",
        export_dir=export_dir,
        timeline_segments=(
            edit_timeline.selected_segments
            if edit_timeline is not None
            else []
        ),
        final_review_report=phase_2b_final_review_report,
        boundary_evidence_report=universal_boundary_evidence_report,
        validator_result=validator_result,
        render_path=final_video_path,
    )
    phase_2b_stabilization_paths = _write_phase_2b_stabilization_result(
        job,
        phase_2b_stabilization_result,
    )
    phase_2b_stabilization_review_paths = _write_phase_2b_stabilization_review(
        job,
        phase_2b_stabilization_result,
    )
    _phase_2b_warning_count = sum(
        [
            phase_2b_stabilization_result.missing_thumbnail_known_warning,
            phase_2b_stabilization_result.high_boundary_review_warning,
            phase_2b_stabilization_result.transcript_boundary_precision_warning,
        ]
    )
    print(
        f"[gaming_pipeline] PHASE_2B_STABILIZATION {job.job_id} "
        f"status={phase_2b_stabilization_result.status} "
        f"ready={str(phase_2b_stabilization_result.phase_2b_ready_to_close).lower()} "
        f"timeline={phase_2b_stabilization_result.timeline_segments} "
        f"review={phase_2b_stabilization_result.final_review_segments} "
        f"warnings={_phase_2b_warning_count}"
    )
    if phase_2b_stabilization_paths:
        print(
            f"[gaming_pipeline] PHASE_2B_STABILIZATION_FILE {job.job_id} "
            f"path={phase_2b_stabilization_paths[-1]}"
        )

    # ------------------------------------------------------------------
    # 11) Repositories speichern
    # ------------------------------------------------------------------
    # Highlight-Daten werden export_path-los gespeichert -
    # pipeline_runner Ã¼bergibt export_path nach RÃ¼ckkehr.
    _highlight_repo_data = {
        "edit_signals":          edit_signals,
        "energy_curve_result":   energy_curve_result,
        "gameplay_vision_result": gameplay_vision_result,
        "sentence_timeline_result": sentence_timeline_result,
        "audio_role_result":    audio_role_result,
        "gameplay_event_result": gameplay_event_result,
        "gameplay_state_result": (
            gameplay_state_result.to_dict()
            if gameplay_state_result is not None
            else None
        ),
        "universal_moment_result": universal_moment_result.to_dict(),
        "universal_moment_debug_report": (
            universal_moment_debug_report.to_dict()
            if universal_moment_debug_report is not None
            else None
        ),
        "universal_moment_soft_decision_report": (
            universal_moment_soft_decision_report.to_dict()
            if universal_moment_soft_decision_report is not None
            else None
        ),
        "universal_role_decision_audit_report": (
            universal_role_decision_audit_report.to_dict()
            if universal_role_decision_audit_report is not None
            else None
        ),
        "universal_context_audit_report": (
            universal_context_audit_report.to_dict()
            if universal_context_audit_report is not None
            else None
        ),
        "universal_boundary_evidence_report": (
            universal_boundary_evidence_report.to_dict()
            if universal_boundary_evidence_report is not None
            else None
        ),
        "phase_2b_final_review_report": (
            phase_2b_final_review_report.to_dict()
            if phase_2b_final_review_report is not None
            else None
        ),
        "phase_2b_stabilization_result": (
            phase_2b_stabilization_result.to_dict()
            if phase_2b_stabilization_result is not None
            else None
        ),
        "round_phase_result":    round_phase_result,
        "facecam_emotion_result": facecam_emotion_result,
        "cut_indicator_result":  cut_indicator_result,
        "cut_profile":           cut_profile,
        "indicator_fusion_note": _fusion_timeline_note,
        "highlight_candidates":  highlight_result["highlight_candidates"],
        "weak_zones":            highlight_result["weak_zones"],
        "summary":               highlight_result["summary"],
    }

    _timeline_to_save      = edit_timeline
    _reframe_to_save       = reframe_plan
    _dynamic_plan_to_save  = dynamic_edit_plan

    # ------------------------------------------------------------------
    # 12) Job-Status ist bereits Ã¼ber state transitions auf RENDERED gesetzt
    # ------------------------------------------------------------------
    try:
        job_repo.save_job(job=job, export_path=None, publish_package=None, shorts_paths=[])
    except Exception:
        pass  # pipeline_runner kÃ¼mmert sich ums finale Speichern

    print(f"[gaming_pipeline] DONE      {job.job_id}  status=rendered")

    return {
        # JSON Profile
        "json_profile":          json_profile,
        "profile_snapshot_path": profile_snapshot_path,
        "profile_metadata":      profile_metadata,
        "profile_id":            json_profile.get("profile_id"),
        "quality_mode":          json_profile.get("quality_mode"),
        "cut_aggressiveness":    json_profile.get("cut_aggressiveness"),
        "music_enabled":         json_profile.get("music_enabled"),
        "source_aspect_ratio":   json_profile.get("source_aspect_ratio"),
        "target_format":         json_profile.get("target_format"),
        "reframing_mode":        json_profile.get("reframing_mode"),
        "camera_zoom_enabled":   json_profile.get("camera_zoom_enabled"),
        "gameplay_zoom_enabled": json_profile.get("gameplay_zoom_enabled"),
        "profile_version":       json_profile.get("version"),
        # Analyse
        "transcript_result":     transcript_result,
        "hook_keyword_result":   hook_keyword_result,
        "sentence_timeline_result": sentence_timeline_result,
        "analysis_result":       analysis_result,
        "edit_decision":         edit_decision,
        # Highlight-Kette
        "edit_signals":          edit_signals,
        "energy_curve_result":   energy_curve_result,
        "gameplay_vision_result": gameplay_vision_result,
        "audio_role_result":    audio_role_result,
        "gameplay_event_result": gameplay_event_result,
        "gameplay_state_result": gameplay_state_result,
        "universal_moment_result": universal_moment_result,
        "universal_moment_debug_report": universal_moment_debug_report,
        "universal_moment_soft_decision_report": universal_moment_soft_decision_report,
        "universal_role_decision_audit_report": universal_role_decision_audit_report,
        "universal_context_audit_report": universal_context_audit_report,
        "universal_boundary_evidence_report": universal_boundary_evidence_report,
        "phase_2b_final_review_report": phase_2b_final_review_report,
        "phase_2b_stabilization_result": phase_2b_stabilization_result,
        "universal_moment_debug_paths": list(universal_moment_debug_paths),
        "universal_moment_soft_decision_paths": list(universal_moment_soft_decision_paths),
        "universal_role_decision_audit_paths": list(universal_role_decision_audit_paths),
        "universal_context_audit_paths": list(universal_context_audit_paths),
        "universal_boundary_evidence_paths": list(universal_boundary_evidence_paths),
        "phase_2b_final_review_paths": list(phase_2b_final_review_paths),
        "universal_moment_review_paths": list(universal_moment_review_paths),
        "phase_2b_stabilization_paths": list(phase_2b_stabilization_paths),
        "phase_2b_stabilization_review_paths": list(phase_2b_stabilization_review_paths),
        "round_phase_result":    round_phase_result,
        "facecam_emotion_result": facecam_emotion_result,
        "cut_indicator_result":  cut_indicator_result,
        "cut_profile":           cut_profile,
        "highlight_candidates":  highlight_result["highlight_candidates"],
        "weak_zones":            highlight_result["weak_zones"],
        "highlight_summary":     highlight_result["summary"],
        # Planung
        "edit_timeline":         edit_timeline,
        "reframe_plan":          reframe_plan,
        "dynamic_edit_plan":     dynamic_edit_plan,
        # Render-Ergebnis
        "final_video_path":      final_video_path,
        "subtitles":             subtitles,
        # Metadaten
        "title_package":         title_package,
        "metadata":              metadata,
        # Validierung
        "validator_result":      validator_result,
        # Repo-Daten (fÃ¼r pipeline_runner zum Speichern)
        "_highlight_repo_data":  _highlight_repo_data,
        "_timeline_to_save":     _timeline_to_save,
        "_reframe_to_save":      _reframe_to_save,
        "_dynamic_plan_to_save": _dynamic_plan_to_save,
    }
