"""Gaming Pipeline — core/gaming_pipeline.py

Isoliertes Pipeline-Modul für gaming_main und gaming_uncut.
Output: <export_dir>/<job_id>/<job_id>_final.mp4

Entfernt gegenüber app.py (werden in späteren Phasen separat gebaut):
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
from core.silence_detection_runner import run_silence_detection_for_job
from core.silence_classifier_runner import run_silence_classifier_for_job
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
    """Dependency-Container für die Gaming-Pipeline.

    Gibt ein Dict mit allen benötigten Service-Instanzen zurück.
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
    """Führt die vollständige Gaming-Render-Pipeline für einen Job aus.

    Pipeline-Schritte:
      1) GamingAnalyzer + GamingCutter  → analysis + edit_decision
      2) EditSignalExtractor            → edit_signals
      3) HighlightSelector              → highlights
      4) LongformTimelineBuilder        → edit_timeline  (wenn longform)
      5) ReframingCore                  → reframe_plan
      6) ReactionMomentDetector
         + ZoomPacingEngine             → dynamic_edit_plan
      7) FinalRenderDriver / RenderProcessor → final_video_path
      8) SubtitleProcessor              → subtitles
      9) TitleGenerator + MetadataGenerator → title + metadata
     10) Validator                      → validator_result
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
        silence_classifier_report = run_silence_classifier_for_job(
            job=job,
            profile=json_profile if isinstance(json_profile, dict) else None,
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
    # 4) Longform-Timeline  (nur wenn Voraussetzungen erfüllt)
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
    # 7) Render — FinalRenderDriver wenn Timeline vorhanden,
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
    print(f"[gaming_pipeline] RENDER    {job.job_id}  → {final_video_path}")

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
    # 10) Validator  (kein Thumbnail → None)
    # ------------------------------------------------------------------
    validator_result = validator.validate(
        job,
        final_video_path,
        title_package,
        metadata,
        None,   # thumbnail_package — wird in Phase 2.5 gebaut
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
    # Highlight-Daten werden export_path-los gespeichert —
    # pipeline_runner übergibt export_path nach Rückkehr.
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
    # 12) Job-Status ist bereits über state transitions auf RENDERED gesetzt
    # ------------------------------------------------------------------
    try:
        job_repo.save_job(job=job, export_path=None, publish_package=None, shorts_paths=[])
    except Exception:
        pass  # pipeline_runner kümmert sich ums finale Speichern

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
        # Repo-Daten (für pipeline_runner zum Speichern)
        "_highlight_repo_data":  _highlight_repo_data,
        "_timeline_to_save":     _timeline_to_save,
        "_reframe_to_save":      _reframe_to_save,
        "_dynamic_plan_to_save": _dynamic_plan_to_save,
    }
