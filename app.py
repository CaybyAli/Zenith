from __future__ import annotations

import os
import json

from shared.channel_policies import (
    get_channel_policy,
    requires_manual_approval,
    is_channel_enabled,
)

from core.intake_manager import IntakeManager
from core.job_store import JobStore
from core.mode_controller import ModeController
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from core.routing_engine import RoutingEngine
from shared.enums import ChannelType, Mode, TargetFormat
from shared.runtime_modes import RuntimeAction

from core.edit_signal_extractor import EditSignalExtractor
from core.highlight_selector import HighlightSelector
from core.highlight_candidate_repository import HighlightCandidateRepository

from core.music_apply_processor import MusicApplyProcessor

from core.longform_timeline_builder import LongformTimelineBuilder
from core.edit_timeline_repository import EditTimelineRepository

from core.music_application_builder import MusicApplicationBuilder
from core.music_application_plan_repository import MusicApplicationPlanRepository

from core.reaction_moment_detector import ReactionMomentDetector
from core.zoom_pacing_engine import ZoomPacingEngine
from core.dynamic_edit_plan_repository import DynamicEditPlanRepository

from core.music_cue_engine import MusicCueEngine
from core.audio_mix_planner import AudioMixPlanner
from core.music_cue_plan_repository import MusicCuePlanRepository
from core.final_edit_integration import FinalEditIntegration

from core.reframing_core import ReframingCore
from core.reframe_plan_repository import ReframePlanRepository

from core.local_music_catalog_repository import LocalMusicCatalogRepository
from core.local_music_selector import LocalMusicSelector
from core.local_music_selection_repository import LocalMusicSelectionRepository

from core.music_apply_timeline_resolver import MusicApplyTimelineResolver
from core.music_apply_timeline_repository import MusicApplyTimelineRepository

from core.final_render_driver import FinalRenderDriver
from core.gaming_analyzer import GamingAnalyzer
from core.gaming_cutter import GamingCutter
from core.render_processor import RenderProcessor
from core.subtitle_processor import SubtitleProcessor
from core.title_generator import TitleGenerator
from core.metadata_generator import MetadataGenerator
from core.thumbnail_forge import ThumbnailForge
from core.ai_thumbnail_forge import AIThumbnailForge
from core.validator import Validator
from core.autopublish_gate import AutopublishGate
from core.publish_package_builder import PublishPackageBuilder
from core.publisher import Publisher
from core.export_manager import ExportManager
from core.content_classifier import ContentClassifier
from core.inbox_scanner import InboxScanner
from core.scheduler import Scheduler
from core.faceless_brief_builder import FacelessBriefBuilder
from core.faceless_asset_builder import FacelessAssetBuilder
from core.faceless_assembler import FacelessAssembler
from core.shorts_decision_engine import ShortsDecisionEngine
from core.shorts_generator import ShortsGenerator

from core.job_repository import JobRepository
from core.job_loader import JobLoader

runtime_mode_controller = RuntimeModeController()
vacation_controller = VacationController()


def is_runtime_action_allowed(action, controller=None):
    active_controller = controller or runtime_mode_controller
    state = active_controller.get_state()
    allowed = action in active_controller.get_allowed_actions(state.mode)

    if not allowed:
        print(
            "[App] Runtime action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| mode:",
            state.mode.value,
        )

    return allowed


def get_effective_operation_mode(controller=None):
    active_controller = controller or vacation_controller
    return active_controller.get_effective_mode()


def is_vacation_action_allowed(action, controller=None):
    active_controller = controller or vacation_controller
    active = active_controller.is_active_now()

    blocked_actions = {
        RuntimeAction.CONTENT_PIPELINE,
        RuntimeAction.FACELESS_PIPELINE,
        RuntimeAction.RERENDER_PIPELINE,
    }

    allowed = (not active) or (action not in blocked_actions)

    if not allowed:
        print(
            "[App] Vacation action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| effective_mode:",
            active_controller.get_effective_mode().value,
        )

    return allowed


def build_thumbnail_forge():
    thumbnail_backend = os.getenv("ZENITH_THUMBNAIL_BACKEND", "frame").strip().lower()

    if thumbnail_backend == "frame":
        return ThumbnailForge()

    if thumbnail_backend == "ai":
        return AIThumbnailForge()

    raise ValueError(f"Unsupported thumbnail backend: {thumbnail_backend}")
    
def is_music_intelligence_enabled_for_channel(channel_type) -> bool:
    return channel_type == ChannelType.GAMING_MAIN    


def load_local_music_assets_for_channel(channel_type):
    if channel_type != ChannelType.GAMING_MAIN:
        return []

    return LocalMusicCatalogRepository().load_assets()

def get_primary_publish_package(publish_packages):
    if not publish_packages:
        raise ValueError("No publish packages resolved")

    return publish_packages[0]


def summarize_publish_results(publish_results, fallback_package):
    from models.publish_result import PublishResult

    if not publish_results:
        return PublishResult(
            job_id=fallback_package.job_id,
            platform=fallback_package.platform,
            publish_status="blocked",
            message=(
                f"No publish results generated for "
                f"{fallback_package.platform.value}"
            ),
        )

    for result in publish_results:
        if result.publish_status == "published":
            return result

    for result in publish_results:
        if result.publish_status == "queued_for_approval":
            return result

    for result in publish_results:
        if result.publish_status == "unsupported_backend":
            return PublishResult(
                job_id=result.job_id,
                platform=result.platform,
                publish_status="policy_resolved",
                message=(
                    f"Policy resolved for {result.platform.value}, "
                    f"but no uploader backend is implemented"
                ),
            )

    for result in publish_results:
        if result.publish_status == "scheduled":
            return result

    for result in publish_results:
        if result.publish_status == "waiting_for_review":
            return result

    return publish_results[0]


def run_pipeline(video_path, channel_type, source_job_id=None, is_rerender=False):
    from core.content_variant_builder import ContentVariantBuilder
    from models.publish_result import PublishResult

    if isinstance(channel_type, str):
        channel_key = channel_type.strip().lower()

        channel_aliases = {
            "main": ChannelType.GAMING_MAIN,
            "gaming_main": ChannelType.GAMING_MAIN,
            "uncut": ChannelType.GAMING_UNCUT,
            "gaming_uncut": ChannelType.GAMING_UNCUT,
        }

        if channel_key not in channel_aliases:
            raise ValueError(f"Unsupported channel_type for rerender: {channel_type}")

        channel_type = channel_aliases[channel_key]

    runtime_action = (
        RuntimeAction.RERENDER_PIPELINE
        if is_rerender or source_job_id
        else RuntimeAction.CONTENT_PIPELINE
    )

    if not is_runtime_action_allowed(runtime_action):
        raise RuntimeError(
            f"Runtime action blocked in app.run_pipeline: {runtime_action.value}"
        )

    if not is_vacation_action_allowed(runtime_action):
        raise RuntimeError(
            f"Vacation action blocked in app.run_pipeline: {runtime_action.value}"
        )

    effective_mode = get_effective_operation_mode()

    job_store = JobStore(db_path="data/jobs.json")
    intake = IntakeManager(job_store=job_store)
    router = RoutingEngine()
    modes = ModeController(initial_mode=effective_mode)

    analyzer = GamingAnalyzer()
    cutter = GamingCutter()
    renderer = RenderProcessor()
    subtitle_processor = SubtitleProcessor()
    title_gen = TitleGenerator()
    metadata_gen = MetadataGenerator()
    thumbnail_forge = build_thumbnail_forge()
    validator = Validator()
    autopublish_gate = AutopublishGate()
    publish_package_builder = PublishPackageBuilder()
    export_manager = ExportManager()
    shorts_engine = ShortsDecisionEngine()
    shorts_generator = ShortsGenerator()
    repo = JobRepository()

    print("RUN PIPELINE:")
    print("video_path:", video_path)
    print("channel_type:", channel_type)
    print("DEBUG 1: run_pipeline wirklich in echter Funktion angekommen")

    if channel_type not in GAMING_CHANNEL_CONFIG:
        raise ValueError(f"Unsupported channel_type for rerender: {channel_type}")

    config = GAMING_CHANNEL_CONFIG[channel_type]

    job = intake.create_gaming_job(
        channel_type=channel_type,
        raw_video_path=video_path,
        target_format=config["target_format"],
        target_platforms=config["target_platforms"],
        mode=modes.get_mode(),
    )

    routed_job = router.route(job)
    job_store.update_job(routed_job)

    print("Created rerender job:")
    print(routed_job)
    print("DEBUG 2: Job wurde wirklich erstellt")

    if channel_type == ChannelType.GAMING_UNCUT:
        classifier = ContentClassifier()
        content_type = classifier.classify(routed_job)
        print("Uncut content type:")
        print(content_type)

    analysis_result = analyzer.analyze(routed_job)
    print("Analysis result:")
    print(analysis_result)

    edit_decision = cutter.build_cut(routed_job, analysis_result)
    print("Edit decision:")
    print(edit_decision)

    shorts_decision = shorts_engine.decide(routed_job, analysis_result, edit_decision)
    print("Shorts decision:")
    print(shorts_decision)

    final_video_path = renderer.render(routed_job, edit_decision)
    print("Final video created:")
    print(final_video_path)

    subtitles = subtitle_processor.generate(routed_job, edit_decision)
    print("Subtitles:")
    print(subtitles)

    title_package = title_gen.generate(routed_job)
    print("Title:")
    print(title_package)

    metadata = metadata_gen.generate(routed_job, title_package)
    print("Metadata:")
    print(metadata)

    thumbnail_package = thumbnail_forge.generate(routed_job, final_video_path)
    print("Thumbnail:")
    print(thumbnail_package)

    validator_result = validator.validate(
        routed_job,
        final_video_path,
        title_package,
        metadata,
        thumbnail_package,
    )
    print("Validator:")
    print(validator_result)

    publish_decision = autopublish_gate.decide(routed_job, validator_result)
    print("Publish decision:")
    print(publish_decision)

    content_variants = ContentVariantBuilder().build(
        job=routed_job,
        video_path=final_video_path,
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path=None,
        source_export_path=None,
    )
    print("Content variants:")
    print(content_variants)

    publish_packages = publish_package_builder.build(content_variants)
    primary_publish_package = get_primary_publish_package(publish_packages)

    print("Publish packages:")
    print(publish_packages)

    shorts = shorts_generator.generate(
        primary_publish_package,
        shorts_decision,
        platform_targets=routed_job.target_platforms,
    )
    print("Generated shorts:")
    print(shorts)

    routed_job.review_status = "pending"
    routed_job.is_scheduled = False
    routed_job.scheduled_at = None
    job_store.update_job(routed_job)

    publish_result = PublishResult(
        job_id=primary_publish_package.job_id,
        platform=primary_publish_package.platform,
        publish_status="waiting_for_review",
        message="Rerender completed and is waiting for review",
    )
    print("Publish result:")
    print(publish_result)

    export_path = save_pipeline_result(
        job=routed_job,
        primary_publish_package=primary_publish_package,
        content_variants=content_variants,
        shorts_paths=shorts,
        export_manager=export_manager,
        repo=repo,
    )

    if is_rerender or source_job_id:
        job_file = os.path.join(export_path, "job.json")

        with open(job_file, "r", encoding="utf-8") as f:
            job_data = json.load(f)

        job_data["source_job_id"] = source_job_id
        job_data["is_rerender"] = is_rerender

        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=4, ensure_ascii=False)

        print("RERENDER METADATA GESPEICHERT:")
        print("source_job_id:", source_job_id)
        print("is_rerender:", is_rerender)

    print("RERENDER PIPELINE DONE:")
    print("new job_id:", routed_job.job_id)

    return routed_job.job_id


def enrich_job_with_review_scores(job, publish_package, shorts_paths):
    from shared.job_scoring import score_job_with_inputs

    title_text = (publish_package.title or "").strip()
    description_text = (publish_package.description or "").strip()
    shorts_count = len(shorts_paths or [])

    has_video = bool(publish_package.video_path and os.path.exists(publish_package.video_path))
    has_thumbnail = bool(publish_package.thumbnail_path and os.path.exists(publish_package.thumbnail_path))

    quality_score = 8.0 if has_video and has_thumbnail else 6.0 if has_video else 4.5
    hook_score = 7.5 if len(title_text) >= 20 else 6.0 if title_text else 4.5
    editing_score = 7.5 if has_video else 5.0
    retention_potential_score = 7.5 if description_text and shorts_count >= 1 else 6.5 if description_text else 5.5
    shorts_potential_score = 8.0 if shorts_count >= 2 else 7.0 if shorts_count == 1 else 5.0

    score_job_with_inputs(
        job,
        quality_score=quality_score,
        hook_score=hook_score,
        editing_score=editing_score,
        retention_potential_score=retention_potential_score,
        shorts_potential_score=shorts_potential_score,
    )
def save_pipeline_result(
    job,
    primary_publish_package,
    content_variants,
    shorts_paths,
    export_manager,
    repo,
):
    from core.content_variant_repository import ContentVariantRepository

    enrich_job_with_review_scores(job, primary_publish_package, shorts_paths)

    export_path = export_manager.export(primary_publish_package)
    repo.save_job(
        job=job,
        export_path=export_path,
        publish_package=primary_publish_package,
        shorts_paths=shorts_paths,
    )

    for variant in content_variants:
        variant.source_export_path = export_path
        variant.touch()

    ContentVariantRepository().save_variants(export_path, content_variants)
    return export_path

def resolve_publish_results(
    job,
    publish_packages,
    publish_decision,
    publisher,
    scheduler=None,
):
    from models.publish_result import PublishResult

    primary_publish_package = get_primary_publish_package(publish_packages)

    channel_group = get_channel_policy(
        primary_publish_package.channel_type.value
    ).channel_group.capitalize()

    if requires_manual_approval(primary_publish_package.channel_type.value):
        if job.review_status != "approved" or not job.is_scheduled:
            return [
                PublishResult(
                    job_id=package.job_id,
                    platform=package.platform,
                    publish_status="waiting_for_review",
                    message=(
                        f"{channel_group} video for {package.platform.value} "
                        f"is waiting for review or scheduling"
                    ),
                )
                for package in publish_packages
            ]

        if scheduler and not scheduler.is_due(job.scheduled_at):
            return [
                PublishResult(
                    job_id=package.job_id,
                    platform=package.platform,
                    publish_status="scheduled",
                    message=(
                        f"{channel_group} video for {package.platform.value} "
                        f"is scheduled for {job.scheduled_at}"
                    ),
                )
                for package in publish_packages
            ]

        if scheduler:
            return [
                publisher.publish(package, publish_decision)
                for package in publish_packages
            ]

        return [
            PublishResult(
                job_id=package.job_id,
                platform=package.platform,
                publish_status="waiting_for_review",
                message=(
                    f"{channel_group} video for {package.platform.value} "
                    f"is waiting for review or scheduling"
                ),
            )
            for package in publish_packages
        ]

    return [
        publisher.publish(package, publish_decision)
        for package in publish_packages
    ]

def build_publish_artifacts(
    job,
    edit_decision,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    final_edit_package=None,
    music_application_plan=None,
    music_apply_timeline=None,
):
    import inspect
    from core.content_variant_builder import ContentVariantBuilder

    render_signature = inspect.signature(renderer.render)
    render_kwargs = {}

    if "final_edit_package" in render_signature.parameters:
        render_kwargs["final_edit_package"] = final_edit_package

    if "music_application_plan" in render_signature.parameters:
        render_kwargs["music_application_plan"] = music_application_plan

    final_video_path = renderer.render(
        job,
        edit_decision,
        **render_kwargs,
    )

    music_apply_result = MusicApplyProcessor().apply(
        rendered_video_path=final_video_path,
        music_application_plan=music_application_plan,
        channel_type=job.channel_type.value,
        music_apply_timeline=music_apply_timeline,
    )

    if music_apply_result.get("music_applied"):
        final_video_path = str(music_apply_result["output_video_path"])

    subtitles = subtitle_processor.generate(job, edit_decision)

    title_package = title_gen.generate(job)
    metadata = metadata_gen.generate(job, title_package)
    thumbnail_package = thumbnail_forge.generate(job, final_video_path)

    validator_result = validator.validate(
        job,
        final_video_path,
        title_package,
        metadata,
        thumbnail_package,
    )

    content_variants = ContentVariantBuilder().build(
        job=job,
        video_path=final_video_path,
        title_package=title_package,
        metadata=metadata,
        thumbnail_package=thumbnail_package,
        subtitle_path=None,
        source_export_path=None,
    )

    publish_packages = publish_package_builder.build(content_variants)

    return {
        "final_video_path": final_video_path,
        "music_apply_result": music_apply_result,
        "subtitles": subtitles,
        "title_package": title_package,
        "metadata": metadata,
        "thumbnail_package": thumbnail_package,
        "validator_result": validator_result,
        "content_variants": content_variants,
        "publish_packages": publish_packages,
    }

def finalize_pipeline_result(
    job,
    content_variants,
    publish_packages,
    validator_result,
    shorts_decision,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    scheduler=None,
):
    primary_publish_package = get_primary_publish_package(publish_packages)

    publish_decision = autopublish_gate.decide(job, validator_result)

    shorts_paths = shorts_generator.generate(
        primary_publish_package,
        shorts_decision,
        platform_targets=job.target_platforms,
    )

    publish_results = resolve_publish_results(
        job=job,
        publish_packages=publish_packages,
        publish_decision=publish_decision,
        publisher=publisher,
        scheduler=scheduler,
    )

    publish_result = summarize_publish_results(
        publish_results,
        primary_publish_package,
    )

    export_path = save_pipeline_result(
        job=job,
        primary_publish_package=primary_publish_package,
        content_variants=content_variants,
        shorts_paths=shorts_paths,
        export_manager=export_manager,
        repo=repo,
    )

    return {
        "publish_decision": publish_decision,
        "shorts_paths": shorts_paths,
        "publish_result": publish_result,
        "publish_results": publish_results,
        "export_path": export_path,
    }

def create_and_route_gaming_job(
    intake,
    router,
    job_store,
    *,
    channel_type,
    raw_video_path,
    target_format,
    target_platforms,
    mode,
):
    job = intake.create_gaming_job(
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        target_format=target_format,
        target_platforms=target_platforms,
        mode=mode,
    )

    routed_job = router.route(job)
    job_store.update_job(routed_job)
    return routed_job

def build_gaming_decisions(job, analyzer, cutter, shorts_engine):
    analysis_result = analyzer.analyze(job)
    edit_decision = cutter.build_cut(job, analysis_result)
    shorts_decision = shorts_engine.decide(job, analysis_result, edit_decision)

    return {
        "analysis_result": analysis_result,
        "edit_decision": edit_decision,
        "shorts_decision": shorts_decision,
    }

def run_gaming_pipeline_for_job(
    job,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
):
    from models.music_cue_plan import MusicCuePlan

    decisions = build_gaming_decisions(
        job,
        analyzer,
        cutter,
        shorts_engine,
    )

    signal_extractor = EditSignalExtractor()
    highlight_selector = HighlightSelector()

    edit_signals = signal_extractor.extract(
        job,
        decisions["analysis_result"],
    )

    highlight_result = highlight_selector.select(
        job,
        decisions["analysis_result"],
        edit_signals,
    )

    edit_timeline = None
    if (
        job.target_format == TargetFormat.LONGFORM
        and decisions["analysis_result"].usable_for_longform
        and highlight_result["highlight_candidates"]
    ):
        edit_timeline = LongformTimelineBuilder().build(
            job=job,
            analysis_result=decisions["analysis_result"],
            highlight_candidates=highlight_result["highlight_candidates"],
            weak_zones=highlight_result["weak_zones"],
        )

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

    if dynamic_edit_plan:
            print("\n[DEBUG] ========== ZOOM DEBUG ==========")
            print(f"[DEBUG] Zoom-Instructions: {len(dynamic_edit_plan.zoom_instructions)}")
            for i, zoom in enumerate(dynamic_edit_plan.zoom_instructions):
                print(f"[DEBUG]   Zoom {i+1}: seg={zoom.segment_id[:8]}, time={zoom.start_time:.1f}s-{zoom.end_time:.1f}s, intensity={zoom.intensity:.2f}")
            print("[DEBUG] =====================================\n")

    music_cue_plan = None
    local_music_selections = []
    music_application_plan = None
    music_apply_timeline = None
    final_edit_package = None

    if edit_timeline is not None and dynamic_edit_plan is not None and reframe_plan is not None:
        local_music_assets = []

        if is_music_intelligence_enabled_for_channel(job.channel_type):
            audio_cues = MusicCueEngine().build_cues(
                job=job,
                timeline=edit_timeline,
                dynamic_edit_plan=dynamic_edit_plan,
            )

            audio_mix_instructions = AudioMixPlanner().build_mix_instructions(
                timeline=edit_timeline,
                dynamic_edit_plan=dynamic_edit_plan,
                audio_cues=audio_cues,
            )

            raw_scores: list[float] = [cue.priority for cue in audio_cues]
            raw_scores.extend(
                instruction.music_level
                for instruction in audio_mix_instructions
            )
            music_plan_score = round(
                sum(raw_scores) / len(raw_scores),
                3,
            ) if raw_scores else 0.0

            music_cue_plan = MusicCuePlan(
                plan_id=f"music_{job.job_id}",
                job_id=job.job_id,
                timeline_id=edit_timeline.timeline_id,
                audio_cues=audio_cues,
                audio_mix_instructions=audio_mix_instructions,
                plan_score=music_plan_score,
                notes=[
                    f"audio_cues={len(audio_cues)}",
                    f"audio_mix_instructions={len(audio_mix_instructions)}",
                    "music_provider=epidemic_option",
                    "music_enabled_for_channel=true",
                ],
            )

            local_music_assets = load_local_music_assets_for_channel(job.channel_type)
            local_music_selections = LocalMusicSelector().select_for_plan(
                job=job,
                music_cue_plan=music_cue_plan,
                assets=local_music_assets,
            )

            music_application_plan = MusicApplicationBuilder().build(
                job=job,
                music_cue_plan=music_cue_plan,
                local_music_selections=local_music_selections,
                assets=local_music_assets,
            )

            if music_application_plan is not None:
                music_apply_timeline = MusicApplyTimelineResolver().build(
                    job=job,
                    music_application_plan=music_application_plan,
                )

        final_edit_package = FinalEditIntegration().build(
            timeline=edit_timeline,
            reframe_plan=reframe_plan,
            dynamic_edit_plan=dynamic_edit_plan,
            music_cue_plan=music_cue_plan,
        )

    # When a full EditTimeline is available, use FinalRenderDriver so that
    # all planning layers (segments, reframe, zoom) are consumed.  A thin
    # adapter keeps build_publish_artifacts' renderer interface unchanged.
    active_renderer = renderer
    if edit_timeline is not None and job.raw_video_path:
        _src = job.raw_video_path
        _tl = edit_timeline
        _rf = reframe_plan
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

    artifacts = build_publish_artifacts(
        job=job,
        edit_decision=decisions["edit_decision"],
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=active_renderer,
        subtitle_processor=subtitle_processor,
        final_edit_package=final_edit_package,
        music_application_plan=music_application_plan,
        music_apply_timeline=music_apply_timeline,
    )

    return {
        "analysis_result": decisions["analysis_result"],
        "edit_decision": decisions["edit_decision"],
        "shorts_decision": decisions["shorts_decision"],
        "edit_signals": edit_signals,
        "highlight_candidates": highlight_result["highlight_candidates"],
        "weak_zones": highlight_result["weak_zones"],
        "highlight_summary": highlight_result["summary"],
        "edit_timeline": edit_timeline,
        "reframe_plan": reframe_plan,
        "dynamic_edit_plan": dynamic_edit_plan,
        "music_cue_plan": music_cue_plan,
        "local_music_selections": local_music_selections,
        "music_application_plan": music_application_plan,
        "music_apply_timeline": music_apply_timeline,
        "final_edit_package": final_edit_package,
        "final_video_path": artifacts["final_video_path"],
        "music_apply_result": artifacts["music_apply_result"],
        "subtitles": artifacts["subtitles"],
        "title_package": artifacts["title_package"],
        "metadata": artifacts["metadata"],
        "thumbnail_package": artifacts["thumbnail_package"],
        "validator_result": artifacts["validator_result"],
        "content_variants": artifacts["content_variants"],
        "publish_packages": artifacts["publish_packages"],
    }

def process_gaming_channel(
    *,
    channel_label,
    channel_type,
    raw_video_path,
    target_format,
    target_platforms,
    intake,
    router,
    job_store,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    mode,
    scheduler=None,
    classifier=None,
):
    routed_job = create_and_route_gaming_job(
        intake,
        router,
        job_store,
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        target_format=target_format,
        target_platforms=target_platforms,
        mode=mode,
    )

    print(f"{channel_label} job:")
    print(routed_job)

    if classifier is not None:
        content_type = classifier.classify(routed_job)
        print(f"{channel_label} content type:")
        print(content_type)

    pipeline = run_gaming_pipeline_for_job(
        job=routed_job,
        analyzer=analyzer,
        cutter=cutter,
        shorts_engine=shorts_engine,
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=renderer,
        subtitle_processor=subtitle_processor,
    )

    print(f"{channel_label} analysis result:")
    print(pipeline["analysis_result"])

    print(f"{channel_label} edit decision:")
    print(pipeline["edit_decision"])

    print(f"{channel_label} shorts decision:")
    print(pipeline["shorts_decision"])

    print(f"{channel_label} music apply result:")
    print(pipeline["music_apply_result"])

    print(f"{channel_label} subtitles:")
    print(pipeline["subtitles"])

    print(f"{channel_label} title:")
    print(pipeline["title_package"])

    print(f"{channel_label} metadata:")
    print(pipeline["metadata"])

    print(f"{channel_label} thumbnail:")
    print(pipeline["thumbnail_package"])

    print(f"{channel_label} validator:")
    print(pipeline["validator_result"])

    print(f"{channel_label} publish packages:")
    print(pipeline["publish_packages"])

    finalize = finalize_pipeline_result(
        job=routed_job,
        content_variants=pipeline["content_variants"],
        publish_packages=pipeline["publish_packages"],
        validator_result=pipeline["validator_result"],
        shorts_decision=pipeline["shorts_decision"],
        autopublish_gate=autopublish_gate,
        shorts_generator=shorts_generator,
        publisher=publisher,
        export_manager=export_manager,
        repo=repo,
        scheduler=scheduler,
    )

    print(f"{channel_label} publish decision:")
    print(finalize["publish_decision"])

    print(f"{channel_label} shorts:")
    print(finalize["shorts_paths"])

    print(f"{channel_label} publish result:")
    print(finalize["publish_result"])
    
    highlight_repo = HighlightCandidateRepository()
    highlight_repo.save_result(
        finalize["export_path"],
        edit_signals=pipeline["edit_signals"],
        highlight_candidates=pipeline["highlight_candidates"],
        weak_zones=pipeline["weak_zones"],
        summary=pipeline["highlight_summary"],
    )

    print(f"{channel_label} highlight summary:")
    print(pipeline["highlight_summary"])    
    
    if pipeline["edit_timeline"] is not None:
        timeline_repo = EditTimelineRepository()
        timeline_repo.save_timeline(
            finalize["export_path"],
            pipeline["edit_timeline"],
        )

        print(f"{channel_label} edit timeline:")
        print(
            {
                "timeline_id": pipeline["edit_timeline"].timeline_id,
                "segments": len(pipeline["edit_timeline"].selected_segments),
                "timeline_score": pipeline["edit_timeline"].timeline_score,
            }
        )    

    if pipeline["reframe_plan"] is not None:
        reframe_repo = ReframePlanRepository()
        reframe_repo.save_plan(
            finalize["export_path"],
            pipeline["reframe_plan"],
        )

        print(f"{channel_label} reframe plan:")
        print(
            {
                "plan_id": pipeline["reframe_plan"].plan_id,
                "instructions": len(pipeline["reframe_plan"].instructions),
                "plan_score": pipeline["reframe_plan"].plan_score,
            }
        )

    if pipeline["dynamic_edit_plan"] is not None:
        dynamic_repo = DynamicEditPlanRepository()
        dynamic_repo.save_plan(
            finalize["export_path"],
            pipeline["dynamic_edit_plan"],
        )

        print(f"{channel_label} dynamic edit plan:")
        print(
            {
                "plan_id": pipeline["dynamic_edit_plan"].plan_id,
                "reaction_moments": len(pipeline["dynamic_edit_plan"].reaction_moments),
                "zoom_instructions": len(pipeline["dynamic_edit_plan"].zoom_instructions),
                "plan_score": pipeline["dynamic_edit_plan"].plan_score,
            }
        )        

    if pipeline["music_cue_plan"] is not None:
        music_repo = MusicCuePlanRepository()
        music_repo.save_plan(
            finalize["export_path"],
            pipeline["music_cue_plan"],
        )

        print(f"{channel_label} music cue plan:")
        print(
            {
                "plan_id": pipeline["music_cue_plan"].plan_id,
                "audio_cues": len(pipeline["music_cue_plan"].audio_cues),
                "mix_instructions": len(pipeline["music_cue_plan"].audio_mix_instructions),
                "plan_score": pipeline["music_cue_plan"].plan_score,
            }
        )

    if pipeline["music_application_plan"] is not None:
        music_application_repo = MusicApplicationPlanRepository()
        music_application_repo.save_plan(
            finalize["export_path"],
            pipeline["music_application_plan"],
        )

        print(f"{channel_label} music application plan:")
        print(
            {
                "plan_id": pipeline["music_application_plan"].plan_id,
                "instructions": len(pipeline["music_application_plan"].instructions),
                "application_score": pipeline["music_application_plan"].application_score,
            }
        )        

    if pipeline["music_apply_timeline"] is not None:
        music_apply_timeline_repo = MusicApplyTimelineRepository()
        music_apply_timeline_repo.save_timeline(
            finalize["export_path"],
            pipeline["music_apply_timeline"],
        )

        print(f"{channel_label} music apply timeline:")
        print(
            {
                "timeline_id": pipeline["music_apply_timeline"].timeline_id,
                "segments": len(pipeline["music_apply_timeline"].segments),
                "timeline_score": pipeline["music_apply_timeline"].timeline_score,
            }
        )

    if pipeline["final_edit_package"] is not None:
        print(f"{channel_label} final edit package:")
        print(pipeline["final_edit_package"])

    return {
        "job": routed_job,
        "pipeline": pipeline,
        "finalize": finalize,
    }



def process_configured_gaming_channel(
    *,
    channel_type,
    raw_video_path,
    intake,
    router,
    job_store,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    mode,
    scheduler=None,
):
    config = GAMING_CHANNEL_CONFIG[channel_type]
    classifier = ContentClassifier() if config["uses_classifier"] else None

    return process_gaming_channel(
        channel_label=config["label"],
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        target_format=config["target_format"],
        target_platforms=config["target_platforms"],
        intake=intake,
        router=router,
        job_store=job_store,
        analyzer=analyzer,
        cutter=cutter,
        shorts_engine=shorts_engine,
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=renderer,
        subtitle_processor=subtitle_processor,
        autopublish_gate=autopublish_gate,
        shorts_generator=shorts_generator,
        publisher=publisher,
        export_manager=export_manager,
        repo=repo,
        mode=mode,
        scheduler=scheduler,
        classifier=classifier,
    )

def run_optional_gaming_channel(
    *,
    channel_type,
    raw_video_path,
    intake,
    router,
    job_store,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    mode,
    scheduler=None,
):
    if not raw_video_path:
        print(f"Kein {get_channel_policy(channel_type.value).channel_group.capitalize()}-Video in inbox/{channel_type.value} gefunden")
        return None

    return process_configured_gaming_channel(
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        intake=intake,
        router=router,
        job_store=job_store,
        analyzer=analyzer,
        cutter=cutter,
        shorts_engine=shorts_engine,
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=renderer,
        subtitle_processor=subtitle_processor,
        autopublish_gate=autopublish_gate,
        shorts_generator=shorts_generator,
        publisher=publisher,
        export_manager=export_manager,
        repo=repo,
        mode=mode,
        scheduler=scheduler,
    )
def run_required_gaming_channel(
    *,
    channel_type,
    raw_video_path,
    intake,
    router,
    job_store,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    mode,
    scheduler=None,
):
    if not raw_video_path:
        raise ValueError(f"Keine Datei in inbox/{channel_type.value} gefunden")

    return process_configured_gaming_channel(
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        intake=intake,
        router=router,
        job_store=job_store,
        analyzer=analyzer,
        cutter=cutter,
        shorts_engine=shorts_engine,
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=renderer,
        subtitle_processor=subtitle_processor,
        autopublish_gate=autopublish_gate,
        shorts_generator=shorts_generator,
        publisher=publisher,
        export_manager=export_manager,
        repo=repo,
        mode=mode,
        scheduler=scheduler,
    )
    
# Nächster Schritt
# In app.py DIREKT UNTER:
# def run_required_gaming_channel(
#
# und DIREKT ÜBER:
# GAMING_CHANNEL_CONFIG = {
#
# genau diesen kompletten Block einfügen:

def run_declared_gaming_channel(
    *,
    channel_type,
    raw_video_path,
    intake,
    router,
    job_store,
    analyzer,
    cutter,
    shorts_engine,
    title_gen,
    metadata_gen,
    thumbnail_forge,
    validator,
    publish_package_builder,
    renderer,
    subtitle_processor,
    autopublish_gate,
    shorts_generator,
    publisher,
    export_manager,
    repo,
    mode,
    scheduler=None,
):
    config = GAMING_CHANNEL_CONFIG[channel_type]

    if config["required"]:
        return run_required_gaming_channel(
            channel_type=channel_type,
            raw_video_path=raw_video_path,
            intake=intake,
            router=router,
            job_store=job_store,
            analyzer=analyzer,
            cutter=cutter,
            shorts_engine=shorts_engine,
            title_gen=title_gen,
            metadata_gen=metadata_gen,
            thumbnail_forge=thumbnail_forge,
            validator=validator,
            publish_package_builder=publish_package_builder,
            renderer=renderer,
            subtitle_processor=subtitle_processor,
            autopublish_gate=autopublish_gate,
            shorts_generator=shorts_generator,
            publisher=publisher,
            export_manager=export_manager,
            repo=repo,
            mode=mode,
            scheduler=scheduler,
        )

    return run_optional_gaming_channel(
        channel_type=channel_type,
        raw_video_path=raw_video_path,
        intake=intake,
        router=router,
        job_store=job_store,
        analyzer=analyzer,
        cutter=cutter,
        shorts_engine=shorts_engine,
        title_gen=title_gen,
        metadata_gen=metadata_gen,
        thumbnail_forge=thumbnail_forge,
        validator=validator,
        publish_package_builder=publish_package_builder,
        renderer=renderer,
        subtitle_processor=subtitle_processor,
        autopublish_gate=autopublish_gate,
        shorts_generator=shorts_generator,
        publisher=publisher,
        export_manager=export_manager,
        repo=repo,
        mode=mode,
        scheduler=scheduler,
    )

GAMING_CHANNEL_CONFIG = {
    ChannelType.GAMING_MAIN: {
        "label": "Main",
        "target_format": TargetFormat.SHORT,
        "target_platforms": ["youtube", "tiktok"],
        "uses_classifier": False,
        "required": True,
    },
    ChannelType.GAMING_UNCUT: {
        "label": "Uncut",
        "target_format": TargetFormat.LONGFORM,
        "target_platforms": ["youtube"],
        "shorts_target_platforms": ["youtube", "tiktok", "instagram"],
        "uses_classifier": True,
        "required": False,
    },
}

def main() -> None:
    effective_mode = get_effective_operation_mode()

    job_store = JobStore(db_path="data/jobs.json")
    intake = IntakeManager(job_store=job_store)
    router = RoutingEngine()
    modes = ModeController(initial_mode=effective_mode)

    scanner = InboxScanner()
    files = scanner.scan()

    print("Inbox files:")
    print(files)

    files_by_type = {file["type"]: file["path"] for file in files}

# durch genau diesen Block ersetzen:

    gaming_input_paths = {
        ChannelType.GAMING_MAIN: files_by_type.get(ChannelType.GAMING_MAIN.value),
        ChannelType.GAMING_UNCUT: files_by_type.get(ChannelType.GAMING_UNCUT.value),
    }

    gaming_main_path = gaming_input_paths[ChannelType.GAMING_MAIN]
    if not gaming_main_path:
        raise ValueError(f"Keine Datei in inbox/{ChannelType.GAMING_MAIN.value} gefunden")

    uncut_path = gaming_input_paths[ChannelType.GAMING_UNCUT]

    analyzer = GamingAnalyzer()
    cutter = GamingCutter()
    shorts_engine = ShortsDecisionEngine()
    renderer = RenderProcessor()
    subtitle_processor = SubtitleProcessor()
    title_gen = TitleGenerator()
    metadata_gen = MetadataGenerator()
    thumbnail_forge = build_thumbnail_forge()
    validator = Validator()
    publish_package_builder = PublishPackageBuilder()
    autopublish_gate = AutopublishGate()
    shorts_generator = ShortsGenerator()
    scheduler = Scheduler()
    publisher = Publisher()
    export_manager = ExportManager()
    repo = JobRepository()

# genau diesen Block einfügen:

    gaming_runtime = {
        "intake": intake,
        "router": router,
        "job_store": job_store,
        "analyzer": analyzer,
        "cutter": cutter,
        "shorts_engine": shorts_engine,
        "title_gen": title_gen,
        "metadata_gen": metadata_gen,
        "thumbnail_forge": thumbnail_forge,
        "validator": validator,
        "publish_package_builder": publish_package_builder,
        "renderer": renderer,
        "subtitle_processor": subtitle_processor,
        "autopublish_gate": autopublish_gate,
        "shorts_generator": shorts_generator,
        "publisher": publisher,
        "export_manager": export_manager,
        "repo": repo,
        "mode": modes.get_mode(),
    }

    # ---------------- GAMING PIPELINES ----------------

    if not is_runtime_action_allowed(RuntimeAction.CONTENT_PIPELINE):
        print("Gaming pipelines sind durch Runtime Mode blockiert")
    elif not is_vacation_action_allowed(RuntimeAction.CONTENT_PIPELINE):
        print("Gaming pipelines sind durch Vacation Mode blockiert")
    else:
        for channel_type in [ChannelType.GAMING_MAIN, ChannelType.GAMING_UNCUT]:
            channel_path = gaming_input_paths[channel_type]

            result = run_declared_gaming_channel(
                channel_type=channel_type,
                raw_video_path=channel_path,
                scheduler=scheduler if channel_type == ChannelType.GAMING_MAIN else None,
                **gaming_runtime,
            )

            if channel_type == ChannelType.GAMING_MAIN and result is not None:
                routed_job = result["job"]

                print("Created and routed job:")
                print(routed_job)
                print("Current mode policy:")
                print(modes.get_policy())

    RUN_FACELESS = is_channel_enabled(ChannelType.FACELESS_TREND.value)

    if RUN_FACELESS:
        if not is_runtime_action_allowed(RuntimeAction.FACELESS_PIPELINE):
            print("Faceless pipeline ist durch Runtime Mode blockiert")
        elif not is_vacation_action_allowed(RuntimeAction.FACELESS_PIPELINE):
            print("Faceless pipeline ist durch Vacation Mode blockiert")
        else:
            faceless_job = intake.create_faceless_job(
                topic="sprechende Möbel trend",
                target_format=TargetFormat.SHORT,
                target_platforms=["youtube", "tiktok"],
                mode=modes.get_mode(),
            )

            faceless_routed = router.route(faceless_job)
            job_store.update_job(faceless_routed)

            if requires_manual_approval(faceless_routed.channel_type.value):
                faceless_routed.review_status = "pending"
                faceless_routed.is_scheduled = False
                faceless_routed.scheduled_at = None
                job_store.update_job(faceless_routed)

            print("Faceless job:")
            print(faceless_routed)

            faceless_brief_builder = FacelessBriefBuilder()
            faceless_brief = faceless_brief_builder.build(faceless_routed)

            print("Faceless brief:")
            print(faceless_brief)

            faceless_asset_builder = FacelessAssetBuilder()
            faceless_asset_pack = faceless_asset_builder.build(faceless_brief)

            print("Faceless asset pack:")
            print(faceless_asset_pack)

            faceless_assembler = FacelessAssembler()
            faceless_video_path = faceless_assembler.assemble(faceless_asset_pack)

            print("Faceless video created:")
            print(faceless_video_path)

            faceless_title_package = title_gen.generate(faceless_routed)

            print("Faceless title:")
            print(faceless_title_package)

            faceless_metadata = metadata_gen.generate(
                faceless_routed,
                faceless_title_package,
            )

            print("Faceless metadata:")
            print(faceless_metadata)

            faceless_thumbnail_package = thumbnail_forge.generate(
                faceless_routed,
                faceless_video_path,
            )

            print("Faceless thumbnail:")
            print(faceless_thumbnail_package)

            faceless_validator_result = validator.validate(
                faceless_routed,
                faceless_video_path,
                faceless_title_package,
                faceless_metadata,
                faceless_thumbnail_package,
            )

            print("Faceless validator:")
            print(faceless_validator_result)

            faceless_publish_decision = autopublish_gate.decide(
                faceless_routed,
                faceless_validator_result,
            )

            print("Faceless publish decision:")
            print(faceless_publish_decision)

            from core.content_variant_builder import ContentVariantBuilder
            from core.content_variant_repository import ContentVariantRepository
            from models.publish_result import PublishResult

            faceless_content_variants = ContentVariantBuilder().build(
                job=faceless_routed,
                video_path=faceless_video_path,
                title_package=faceless_title_package,
                metadata=faceless_metadata,
                thumbnail_package=faceless_thumbnail_package,
                subtitle_path=None,
                source_export_path=None,
            )

            faceless_publish_packages = publish_package_builder.build(
                faceless_content_variants
            )
            faceless_primary_publish_package = get_primary_publish_package(
                faceless_publish_packages
            )

            print("Faceless content variants:")
            print(faceless_content_variants)

            print("Faceless publish packages:")
            print(faceless_publish_packages)

            faceless_publish_results = [
                PublishResult(
                    job_id=package.job_id,
                    platform=package.platform,
                    publish_status="waiting_for_review",
                    message=(
                        f"Faceless video for {package.platform.value} is waiting "
                        f"for manual review in dashboard"
                    ),
                )
                for package in faceless_publish_packages
            ]

            faceless_publish_result = summarize_publish_results(
                faceless_publish_results,
                faceless_primary_publish_package,
            )

            print("Faceless publish result:")
            print(faceless_publish_result)

            faceless_export_path = export_manager.export(
                faceless_primary_publish_package
            )

            for variant in faceless_content_variants:
                variant.source_export_path = faceless_export_path
                variant.touch()

            ContentVariantRepository().save_variants(
                faceless_export_path,
                faceless_content_variants,
            )
    else:
        print("Faceless pipeline ist deaktiviert")


    loader = JobLoader()
    loaded_jobs = loader.load_all_jobs()

    print("Loaded jobs:")
    for loaded_job in loaded_jobs:
        policy = get_channel_policy(loaded_job.channel_type.value)
        print(
            loaded_job.job_id,
            loaded_job.channel_type.value,
            policy.channel_group,
            getattr(loaded_job, "title", "NO_TITLE"),
        )

if __name__ == "__main__":
    raise SystemExit(
        "app.py ist kein direkter Startpunkt mehr. Nutze 'python dashboard.py' für das Dashboard oder 'python pipeline_runner.py' für die Pipeline."
    )