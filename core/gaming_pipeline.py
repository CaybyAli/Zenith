"""Gaming Pipeline â€” core/gaming_pipeline.py

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

from core.edit_signal_extractor import EditSignalExtractor
from core.energy_curve_builder import EnergyCurveBuilder
from core.gameplay_vision_analyzer import GameplayVisionAnalyzer
from core.facecam_reaction_analyzer import FacecamReactionAnalyzer
from core.highlight_selector import HighlightSelector
from core.longform_timeline_builder import LongformTimelineBuilder
from core.reframing_core import ReframingCore
from core.reaction_moment_detector import ReactionMomentDetector
from core.zoom_pacing_engine import ZoomPacingEngine
from core.final_render_driver import FinalRenderDriver
from core.ffmpeg_helper import ensure_ffmpeg_on_path

from core.highlight_candidate_repository import HighlightCandidateRepository
from core.edit_timeline_repository import EditTimelineRepository
from core.dynamic_edit_plan_repository import DynamicEditPlanRepository
from core.reframe_plan_repository import ReframePlanRepository
from core.job_repository import JobRepository
from core.job_loader import JobLoader
from core.job_store import JobStore


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

    gameplay_vision_result = None
    if job.channel_type == ChannelType.GAMING_MAIN:
        gameplay_vision_analyzer = services.get("gameplay_vision_analyzer") or GameplayVisionAnalyzer()

        if job.raw_video_path:
            gameplay_vision_result = gameplay_vision_analyzer.analyze_video(
                video_path=str(job.raw_video_path),
                sample_every_seconds=1.0,
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
    # 4) Longform-Timeline  (nur wenn Voraussetzungen erfÃ¼llt)
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
    # 7) Render â€” FinalRenderDriver wenn Timeline vorhanden,
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
        None,   # thumbnail_package â€” wird in Phase 2.5 gebaut
    )
    print(f"[gaming_pipeline] VALIDATE  {job.job_id}  "
          f"status={getattr(validator_result, 'validator_status', '?')}")

    # ------------------------------------------------------------------
    # 11) Repositories speichern
    # ------------------------------------------------------------------
    # Highlight-Daten werden export_path-los gespeichert â€”
    # pipeline_runner Ã¼bergibt export_path nach RÃ¼ckkehr.
    _highlight_repo_data = {
        "edit_signals":          edit_signals,
        "energy_curve_result":   energy_curve_result,
        "gameplay_vision_result": gameplay_vision_result,
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
    job.status = JobStatus.RENDERED
    try:
        job_repo.save_job(job=job, export_path=None, publish_package=None, shorts_paths=[])
    except Exception:
        pass  # pipeline_runner kÃ¼mmert sich ums finale Speichern

    print(f"[gaming_pipeline] DONE      {job.job_id}  status=rendered")

    return {
        # Analyse
        "transcript_result":     transcript_result,
        "hook_keyword_result":   hook_keyword_result,
        "analysis_result":       analysis_result,
        "edit_decision":         edit_decision,
        # Highlight-Kette
        "edit_signals":          edit_signals,
        "energy_curve_result":   energy_curve_result,
        "gameplay_vision_result": gameplay_vision_result,
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



