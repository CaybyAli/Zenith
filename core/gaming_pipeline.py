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

from shared.enums import ChannelType, TargetFormat

from core.gaming_analyzer import GamingAnalyzer
from core.gaming_cutter import GamingCutter
from core.render_processor import RenderProcessor
from core.subtitle_processor import SubtitleProcessor
from core.title_generator import TitleGenerator
from core.metadata_generator import MetadataGenerator
from core.validator import Validator
from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError

from core.edit_signal_extractor import EditSignalExtractor
from core.highlight_selector import HighlightSelector
from core.longform_timeline_builder import LongformTimelineBuilder
from core.reframing_core import ReframingCore
from core.reaction_moment_detector import ReactionMomentDetector
from core.zoom_pacing_engine import ZoomPacingEngine
from core.final_render_driver import FinalRenderDriver

from core.highlight_candidate_repository import HighlightCandidateRepository
from core.edit_timeline_repository import EditTimelineRepository
from core.dynamic_edit_plan_repository import DynamicEditPlanRepository
from core.reframe_plan_repository import ReframePlanRepository
from core.job_repository import JobRepository
from core.job_loader import JobLoader
from core.job_store import JobStore


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
     12) Job-Status → "rendered"

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

    transcript_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        if job.raw_video_path:
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

    # ------------------------------------------------------------------
    # 1) Analyse + Edit-Entscheidung
    # ------------------------------------------------------------------
    analysis_result = analyzer.analyze(job)
    print(f"[gaming_pipeline] ANALYZE   {job.job_id}  done")

    edit_decision = cutter.build_cut(job, analysis_result)
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

    # ------------------------------------------------------------------
    # 4) Longform-Timeline  (nur wenn Voraussetzungen erfüllt)
    # ------------------------------------------------------------------
    edit_timeline = None
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
        )
        print(f"[gaming_pipeline] TIMELINE  {job.job_id}  "
              f"segments={len(edit_timeline.selected_segments)}  "
              f"score={edit_timeline.timeline_score}")

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

    final_video_path = active_renderer.render(job, edit_decision)
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
          f"status={getattr(validator_result, 'validator_status', '?')}")

    # ------------------------------------------------------------------
    # 11) Repositories speichern
    # ------------------------------------------------------------------
    # Highlight-Daten werden export_path-los gespeichert —
    # pipeline_runner übergibt export_path nach Rückkehr.
    _highlight_repo_data = {
        "edit_signals":          edit_signals,
        "highlight_candidates":  highlight_result["highlight_candidates"],
        "weak_zones":            highlight_result["weak_zones"],
        "summary":               highlight_result["summary"],
    }

    _timeline_to_save      = edit_timeline
    _reframe_to_save       = reframe_plan
    _dynamic_plan_to_save  = dynamic_edit_plan

    # ------------------------------------------------------------------
    # 12) Job-Status setzen
    # ------------------------------------------------------------------
    job.status = "rendered"
    try:
        job_repo.save_job(job=job, export_path=None, publish_package=None, shorts_paths=[])
    except Exception:
        pass  # pipeline_runner kümmert sich ums finale Speichern

    print(f"[gaming_pipeline] DONE      {job.job_id}  status=rendered")

    return {
        # Analyse
        "transcript_result":     transcript_result,
        "analysis_result":       analysis_result,
        "edit_decision":         edit_decision,
        # Highlight-Kette
        "edit_signals":          edit_signals,
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
