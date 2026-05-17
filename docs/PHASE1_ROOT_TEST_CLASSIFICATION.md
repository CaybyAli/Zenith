# PROJECT ZENITH — Phase 1.5b Root-Test-Klassifizierung

Diese Datei ersetzt die alte falsche Klassifizierung.

## Kriterium

- LEBEND: alle relevanten importierten Projektmodule sind per `importlib.util.find_spec()` auffindbar.
- VERWAIST: mindestens ein relevanter importierter Modulname ist nicht auffindbar.
- UNKLAR: Datei kann nicht sauber geparst werden.

Es werden auch präfixlose Projektimporte geprüft, z. B. `dashboard`, `publisher_worker`, `rerender_worker`.
Standardbibliothek und bekannte Drittanbieter-Pakete werden ignoriert.

Es wurde nichts verschoben, nichts archiviert und nichts gelöscht.

## Summen

- Root-Tests gesamt: 165
- LEBEND: 30
- VERWAIST: 134
- UNKLAR: 1

## Fehlende Module

| Fehlendes Modul | Anzahl Dateien |
|---|---|
| `app` | 27 |
| `app.finalize_pipeline_result` | 1 |
| `app.is_music_intelligence_enabled_for_channel` | 1 |
| `app.is_runtime_action_allowed` | 1 |
| `app.process_gaming_channel` | 9 |
| `app.run_gaming_pipeline_for_job` | 13 |
| `app.save_pipeline_result` | 1 |
| `core.access_context_service` | 1 |
| `core.access_context_service.AccessContextService` | 1 |
| `core.audio_mix_planner` | 1 |
| `core.audio_mix_planner.AudioMixPlanner` | 1 |
| `core.authorization_service` | 1 |
| `core.authorization_service.AuthorizationService` | 1 |
| `core.comparison_view_builder` | 1 |
| `core.comparison_view_builder.ComparisonViewBuilder` | 1 |
| `core.connectors.google_trends_rss_connector` | 1 |
| `core.connectors.google_trends_rss_connector.GoogleTrendsRssConnector` | 1 |
| `core.connectors.youtube_most_popular_connector` | 1 |
| `core.connectors.youtube_most_popular_connector.YouTubeMostPopularConnector` | 1 |
| `core.content_variant_builder` | 7 |
| `core.content_variant_builder.ContentVariantBuilder` | 7 |
| `core.content_variant_repository` | 4 |
| `core.content_variant_repository.ContentVariantRepository` | 4 |
| `core.cross_platform_publish_orchestrator` | 7 |
| `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator` | 7 |
| `core.faceless_pipeline.FacelessPipeline` | 1 |
| `core.faceless_pipeline._GPT4oEnricher` | 1 |
| `core.feedback_aggregation_service` | 1 |
| `core.feedback_aggregation_service.FeedbackAggregationService` | 1 |
| `core.feedback_context_bridge` | 1 |
| `core.feedback_context_bridge.FeedbackContextBridge` | 1 |
| `core.feedback_dashboard_service` | 1 |
| `core.feedback_dashboard_service.FeedbackDashboardService` | 1 |
| `core.feedback_manager` | 1 |
| `core.feedback_manager.FeedbackManager` | 1 |
| `core.feedback_repository` | 3 |
| `core.feedback_repository.FeedbackRepository` | 3 |
| `core.insight_surface_builder` | 1 |
| `core.insight_surface_builder.InsightSurfaceBuilder` | 1 |
| `core.integrity_scanner` | 3 |
| `core.integrity_scanner.IntegrityScanResult` | 2 |
| `core.integrity_scanner.IntegrityScanner` | 1 |
| `core.jarvis_command_parser` | 1 |
| `core.jarvis_command_parser.JarvisCommandParser` | 1 |
| `core.jarvis_command_service` | 3 |
| `core.jarvis_command_service.JarvisCommandService` | 3 |
| `core.jarvis_presence_service` | 1 |
| `core.jarvis_presence_service.JarvisPresenceService` | 1 |
| `core.jarvis_status_service` | 4 |
| `core.jarvis_status_service.JarvisStatusService` | 4 |
| `core.kpi_dashboard_service` | 1 |
| `core.kpi_dashboard_service.KpiDashboardService` | 1 |
| `core.kpi_view_builder` | 1 |
| `core.kpi_view_builder.KpiViewBuilder` | 1 |
| `core.live_trend_intake_runner` | 2 |
| `core.live_trend_intake_runner.LiveTrendIntakeRunner` | 2 |
| `core.local_music_catalog_repository` | 11 |
| `core.local_music_catalog_repository.LocalMusicCatalogRepository` | 11 |
| `core.local_music_selection_repository` | 2 |
| `core.local_music_selection_repository.LocalMusicSelectionRepository` | 2 |
| `core.local_music_selector` | 3 |
| `core.local_music_selector.LocalMusicSelector` | 3 |
| `core.maintenance_report_builder` | 1 |
| `core.maintenance_report_builder.MaintenanceReportBuilder` | 1 |
| `core.maintenance_runner` | 1 |
| `core.maintenance_runner.MaintenanceRunner` | 1 |
| `core.metrics_attribution_bridge` | 2 |
| `core.metrics_attribution_bridge.MetricsAttributionBridge` | 2 |
| `core.metrics_sync_manager` | 1 |
| `core.metrics_sync_manager.MetricsSyncManager` | 1 |
| `core.music_application_builder` | 2 |
| `core.music_application_builder.MusicApplicationBuilder` | 2 |
| `core.music_application_plan_repository` | 2 |
| `core.music_application_plan_repository.MusicApplicationPlanRepository` | 2 |
| `core.music_apply_processor` | 2 |
| `core.music_apply_processor.MusicApplyProcessor` | 2 |
| `core.music_apply_timeline_repository` | 3 |
| `core.music_apply_timeline_repository.MusicApplyTimelineRepository` | 3 |
| `core.music_apply_timeline_resolver` | 1 |
| `core.music_apply_timeline_resolver.MusicApplyTimelineResolver` | 1 |
| `core.music_cue_engine` | 1 |
| `core.music_cue_engine.MusicCueEngine` | 1 |
| `core.music_cue_plan_repository` | 2 |
| `core.music_cue_plan_repository.MusicCuePlanRepository` | 2 |
| `core.normalized_metrics_repository` | 5 |
| `core.normalized_metrics_repository.NormalizedMetricsRepository` | 5 |
| `core.operations_dashboard_service` | 2 |
| `core.operations_dashboard_service.OperationsDashboardService` | 2 |
| `core.opportunity_manager` | 1 |
| `core.opportunity_manager.OpportunityManager` | 1 |
| `core.opportunity_review_manager` | 1 |
| `core.opportunity_review_manager.OpportunityReviewManager` | 1 |
| `core.opportunity_review_store` | 3 |
| `core.opportunity_review_store.OpportunityReviewStore` | 3 |
| `core.opportunity_store` | 2 |
| `core.opportunity_store.OpportunityStore` | 2 |
| `core.performance_attribution_repository` | 3 |
| `core.performance_attribution_repository.PerformanceAttributionRepository` | 3 |
| `core.platform_policy_resolver` | 1 |
| `core.platform_policy_resolver.PlatformPolicyResolver` | 1 |
| `core.platform_raw_metrics_repository` | 3 |
| `core.platform_raw_metrics_repository.PlatformRawMetricsRepository` | 3 |
| `core.publish_guard` | 1 |
| `core.publish_guard.PublishGuard` | 1 |
| `core.publish_guard_repository` | 2 |
| `core.publish_guard_repository.PublishGuardRepository` | 2 |
| `core.publish_package_builder` | 27 |
| `core.publish_package_builder.PublishPackageBuilder` | 27 |
| `core.publish_result_metrics_bridge` | 2 |
| `core.publish_result_metrics_bridge.PublishResultMetricsBridge` | 2 |
| `core.publish_result_repository` | 11 |
| `core.publish_result_repository.PublishResultRepository` | 11 |
| `core.publisher` | 2 |
| `core.publisher.Publisher` | 2 |
| `core.queue_collision_detector` | 1 |
| `core.queue_collision_detector.QueueCollisionDetector` | 1 |
| `core.queue_collision_resolver` | 2 |
| `core.queue_collision_resolver.QueueCollisionResolver` | 2 |
| `core.queue_collision_snapshot_builder` | 2 |
| `core.queue_collision_snapshot_builder.QueueCollisionSnapshotBuilder` | 2 |
| `core.queue_orchestrator` | 2 |
| `core.queue_orchestrator.QueueOrchestrator` | 2 |
| `core.queue_priority_explainer` | 2 |
| `core.queue_priority_explainer.QueuePriorityExplainer` | 2 |
| `core.queue_priority_manager` | 2 |
| `core.queue_priority_manager.QueuePriorityManager` | 2 |
| `core.queue_priority_snapshot_builder` | 2 |
| `core.queue_priority_snapshot_builder.QueuePrioritySnapshotBuilder` | 2 |
| `core.queue_store` | 11 |
| `core.queue_store.QueueStore` | 11 |
| `core.recovery_executor` | 1 |
| `core.recovery_executor.RecoveryExecutor` | 1 |
| `core.recovery_planner` | 2 |
| `core.recovery_planner.RecoveryPlanner` | 2 |
| `core.retention_planner` | 1 |
| `core.retention_planner.RetentionPlanner` | 1 |
| `core.runtime_mode_controller.RuntimeModeController` | 10 |
| `core.scheduling_policy_evaluator` | 2 |
| `core.scheduling_policy_evaluator.SchedulingPolicyEvaluator` | 2 |
| `core.scheduling_policy_manager` | 4 |
| `core.scheduling_policy_manager.SchedulingPolicyManager` | 4 |
| `core.scheduling_policy_store` | 4 |
| `core.scheduling_policy_store.SchedulingPolicyStore` | 4 |
| `core.scheduling_time_resolver` | 2 |
| `core.scheduling_time_resolver.SchedulingTimeResolver` | 2 |
| `core.shorts_decision_engine` | 1 |
| `core.shorts_decision_engine.ShortsDecisionEngine` | 1 |
| `core.shorts_generator` | 1 |
| `core.shorts_generator.ShortsGenerator` | 1 |
| `core.tiktok_uploader` | 1 |
| `core.tiktok_uploader.TikTokUploadError` | 1 |
| `core.tiktok_uploader.TikTokUploader` | 1 |
| `core.tiktok_uploader._STATUS_MAX_POLLS` | 1 |
| `core.tiktok_uploader._build_caption` | 1 |
| `core.tiktok_uploader._chunk_size_for` | 1 |
| `core.trend_intake_manager` | 3 |
| `core.trend_intake_manager.TrendIntakeManager` | 3 |
| `core.trend_qualification_manager` | 1 |
| `core.trend_qualification_manager.TrendQualificationManager` | 1 |
| `core.trend_qualification_store` | 3 |
| `core.trend_qualification_store.TrendQualificationStore` | 3 |
| `core.trend_store` | 6 |
| `core.trend_store.TrendStore` | 6 |
| `core.vertical_reframe_engine` | 1 |
| `core.vertical_reframe_engine.VerticalReframeEngine` | 1 |
| `core.workspace_repository` | 2 |
| `core.workspace_repository.WorkspaceRepository` | 2 |
| `dashboard` | 16 |
| `dashboard.app` | 9 |
| `dashboard.runtime_mode_controller` | 1 |
| `models.actor_context.ActorContext` | 1 |
| `models.opportunity_review_view.OpportunityReviewView` | 1 |
| `models.queue_entry.QueueEntry` | 9 |
| `models.workspace_membership.WorkspaceMembership` | 2 |
| `publisher_worker` | 8 |
| `publisher_worker.build_publish_packages_from_job_data` | 1 |
| `publisher_worker.is_runtime_action_allowed` | 1 |
| `publisher_worker.summarize_publish_results` | 1 |
| `rerender_worker` | 4 |
| `rerender_worker.is_runtime_action_allowed` | 1 |
| `shared.jarvis_enums` | 4 |
| `shared.jarvis_enums.JarvisCommandType` | 4 |
| `shared.opportunity_enums` | 2 |
| `shared.opportunity_enums.OpportunityLevel` | 2 |
| `shared.opportunity_review_enums` | 3 |
| `shared.opportunity_review_enums.OpportunityReviewStatus` | 3 |
| `shared.queue_enums` | 3 |
| `shared.queue_enums.QueueState` | 3 |
| `shared.role_enums` | 3 |
| `shared.role_enums.ProtectedAction` | 1 |
| `shared.role_enums.RoleType` | 3 |
| `shared.runtime_modes` | 10 |
| `shared.runtime_modes.RuntimeAction` | 10 |
| `shared.runtime_modes.RuntimeMode` | 5 |
| `shared.trend_qualification_enums` | 2 |
| `shared.trend_qualification_enums.LifespanClass` | 2 |

## Einzeltabelle

| Datei | Kategorie | fehlende Module |
|---|---|---|
| `test_access_context_service_smoke.py` | VERWAIST | `core.access_context_service`, `core.access_context_service.AccessContextService`, `core.workspace_repository`, `core.workspace_repository.WorkspaceRepository`, `models.workspace_membership.WorkspaceMembership`, `shared.role_enums`, `shared.role_enums.RoleType` |
| `test_app_runtime_gate_smoke.py` | VERWAIST | `app`, `app.is_runtime_action_allowed`, `core.runtime_mode_controller.RuntimeModeController`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction`, `shared.runtime_modes.RuntimeMode` |
| `test_app_vacation_gate_smoke.py` | VERWAIST | `app`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction` |
| `test_audio_cue_models_smoke.py` | LEBEND |  |
| `test_audio_mix_planner_smoke.py` | VERWAIST | `core.audio_mix_planner`, `core.audio_mix_planner.AudioMixPlanner` |
| `test_authorization_service_smoke.py` | VERWAIST | `core.authorization_service`, `core.authorization_service.AuthorizationService`, `models.actor_context.ActorContext`, `shared.role_enums`, `shared.role_enums.ProtectedAction`, `shared.role_enums.RoleType` |
| `test_content_variant_builder_repository_smoke.py` | VERWAIST | `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.content_variant_repository`, `core.content_variant_repository.ContentVariantRepository` |
| `test_cross_platform_publish_guard_smoke.py` | VERWAIST | `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_guard_repository`, `core.publish_guard_repository.PublishGuardRepository`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_cross_platform_publish_orchestrator_smoke.py` | VERWAIST | `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_dashboard_access_context_surface_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_command_deck_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_feedback_surface_render_smoke.py` | VERWAIST | `dashboard` |
| `test_dashboard_full_operations_layout_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_high_tech_layout_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_high_tech_presence_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_jarvis_panel_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_kpi_surface_render_smoke.py` | VERWAIST | `dashboard` |
| `test_dashboard_role_guard_smoke.py` | VERWAIST | `dashboard`, `dashboard.app`, `dashboard.runtime_mode_controller` |
| `test_dashboard_roles_permissions_surface_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_runtime_gate_smoke.py` | VERWAIST | `core.runtime_mode_controller.RuntimeModeController`, `dashboard`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction`, `shared.runtime_modes.RuntimeMode` |
| `test_dashboard_storage_provider_mutation_smoke.py` | VERWAIST | `dashboard` |
| `test_dashboard_storage_provider_smoke.py` | VERWAIST | `dashboard` |
| `test_dashboard_unified_operations_surface_smoke.py` | VERWAIST | `dashboard`, `dashboard.app` |
| `test_dashboard_vacation_gate_smoke.py` | VERWAIST | `dashboard`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction` |
| `test_dashboard_vacation_smoke.py` | VERWAIST | `dashboard`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction` |
| `test_dynamic_edit_models_smoke.py` | LEBEND |  |
| `test_dynamic_edit_plan_repository_smoke.py` | LEBEND |  |
| `test_edit_signal_extractor_smoke.py` | LEBEND |  |
| `test_edit_timeline_models_smoke.py` | LEBEND |  |
| `test_edit_timeline_repository_smoke.py` | LEBEND |  |
| `test_energy_curve_builder_smoke.py` | UNKLAR |  |
| `test_export_manager_storage_provider_smoke.py` | LEBEND |  |
| `test_facecam_gameplay_separator_smoke.py` | LEBEND |  |
| `test_faceless_pipeline_smoke.py` | VERWAIST | `core.faceless_pipeline.FacelessPipeline`, `core.faceless_pipeline._GPT4oEnricher` |
| `test_feedback_context_bridge_smoke.py` | VERWAIST | `core.feedback_context_bridge`, `core.feedback_context_bridge.FeedbackContextBridge`, `core.feedback_repository`, `core.feedback_repository.FeedbackRepository` |
| `test_feedback_dashboard_service_smoke.py` | VERWAIST | `core.feedback_dashboard_service`, `core.feedback_dashboard_service.FeedbackDashboardService`, `core.feedback_repository`, `core.feedback_repository.FeedbackRepository` |
| `test_feedback_learning_backbone_smoke.py` | VERWAIST | `core.feedback_aggregation_service`, `core.feedback_aggregation_service.FeedbackAggregationService`, `core.feedback_manager`, `core.feedback_manager.FeedbackManager`, `core.feedback_repository`, `core.feedback_repository.FeedbackRepository` |
| `test_final_edit_integration_smoke.py` | LEBEND |  |
| `test_final_render_driver_smoke.py` | LEBEND |  |
| `test_finalize_pipeline_result_variants_smoke.py` | VERWAIST | `app`, `app.finalize_pipeline_result`, `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.content_variant_repository`, `core.content_variant_repository.ContentVariantRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_google_trends_rss_smoke.py` | VERWAIST | `core.connectors.google_trends_rss_connector`, `core.connectors.google_trends_rss_connector.GoogleTrendsRssConnector`, `core.live_trend_intake_runner`, `core.live_trend_intake_runner.LiveTrendIntakeRunner`, `core.trend_intake_manager`, `core.trend_intake_manager.TrendIntakeManager`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_highlight.py` | LEBEND |  |
| `test_highlight_candidate_repository_smoke.py` | LEBEND |  |
| `test_highlight_selector_smoke.py` | LEBEND |  |
| `test_highlight_selector_weak_zone_smoke.py` | LEBEND |  |
| `test_import.py` | LEBEND |  |
| `test_integrity_scanner_smoke.py` | VERWAIST | `core.integrity_scanner`, `core.integrity_scanner.IntegrityScanner` |
| `test_jarvis_blocked_warning_publish_smoke.py` | VERWAIST | `core.jarvis_command_service`, `core.jarvis_command_service.JarvisCommandService`, `core.jarvis_status_service`, `core.jarvis_status_service.JarvisStatusService`, `core.runtime_mode_controller.RuntimeModeController`, `shared.jarvis_enums`, `shared.jarvis_enums.JarvisCommandType` |
| `test_jarvis_command_parser_smoke.py` | VERWAIST | `core.jarvis_command_parser`, `core.jarvis_command_parser.JarvisCommandParser`, `shared.jarvis_enums`, `shared.jarvis_enums.JarvisCommandType` |
| `test_jarvis_command_service_smoke.py` | VERWAIST | `core.jarvis_command_service`, `core.jarvis_command_service.JarvisCommandService`, `core.jarvis_status_service`, `core.jarvis_status_service.JarvisStatusService`, `core.runtime_mode_controller.RuntimeModeController`, `shared.jarvis_enums`, `shared.jarvis_enums.JarvisCommandType` |
| `test_jarvis_presence_service_smoke.py` | VERWAIST | `core.jarvis_presence_service`, `core.jarvis_presence_service.JarvisPresenceService` |
| `test_jarvis_queue_maintenance_smoke.py` | VERWAIST | `core.jarvis_command_service`, `core.jarvis_command_service.JarvisCommandService`, `core.jarvis_status_service`, `core.jarvis_status_service.JarvisStatusService`, `core.queue_store`, `core.queue_store.QueueStore`, `core.runtime_mode_controller.RuntimeModeController`, `models.queue_entry.QueueEntry`, `shared.jarvis_enums`, `shared.jarvis_enums.JarvisCommandType`, `shared.opportunity_enums`, `shared.opportunity_enums.OpportunityLevel`, `shared.opportunity_review_enums`, `shared.opportunity_review_enums.OpportunityReviewStatus`, `shared.queue_enums`, `shared.queue_enums.QueueState`, `shared.trend_qualification_enums`, `shared.trend_qualification_enums.LifespanClass` |
| `test_jarvis_status_service_smoke.py` | VERWAIST | `core.jarvis_status_service`, `core.jarvis_status_service.JarvisStatusService`, `core.runtime_mode_controller.RuntimeModeController` |
| `test_job_loader_storage_provider_smoke.py` | LEBEND |  |
| `test_job_repository_storage_provider_smoke.py` | LEBEND |  |
| `test_job_store_storage_provider_smoke.py` | LEBEND |  |
| `test_kpi_dashboard_service_smoke.py` | VERWAIST | `core.kpi_dashboard_service`, `core.kpi_dashboard_service.KpiDashboardService`, `core.normalized_metrics_repository`, `core.normalized_metrics_repository.NormalizedMetricsRepository`, `core.performance_attribution_repository`, `core.performance_attribution_repository.PerformanceAttributionRepository` |
| `test_kpi_insight_surface_smoke.py` | VERWAIST | `core.comparison_view_builder`, `core.comparison_view_builder.ComparisonViewBuilder`, `core.insight_surface_builder`, `core.insight_surface_builder.InsightSurfaceBuilder`, `core.kpi_view_builder`, `core.kpi_view_builder.KpiViewBuilder` |
| `test_local_music_catalog_repository_smoke.py` | VERWAIST | `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository` |
| `test_local_music_selection_repository_smoke.py` | VERWAIST | `core.local_music_selection_repository`, `core.local_music_selection_repository.LocalMusicSelectionRepository` |
| `test_local_music_selector_channel_guard_smoke.py` | VERWAIST | `core.local_music_selector`, `core.local_music_selector.LocalMusicSelector` |
| `test_local_music_selector_reuse_guard_smoke.py` | VERWAIST | `core.local_music_selector`, `core.local_music_selector.LocalMusicSelector` |
| `test_local_music_selector_smoke.py` | VERWAIST | `core.local_music_selector`, `core.local_music_selector.LocalMusicSelector` |
| `test_longform_timeline_builder_smoke.py` | LEBEND |  |
| `test_maintenance_report_builder_smoke.py` | VERWAIST | `core.maintenance_report_builder`, `core.maintenance_report_builder.MaintenanceReportBuilder` |
| `test_maintenance_runner_smoke.py` | VERWAIST | `core.maintenance_runner`, `core.maintenance_runner.MaintenanceRunner` |
| `test_metrics_to_attribution_chain_smoke.py` | VERWAIST | `core.metrics_attribution_bridge`, `core.metrics_attribution_bridge.MetricsAttributionBridge`, `core.normalized_metrics_repository`, `core.normalized_metrics_repository.NormalizedMetricsRepository`, `core.performance_attribution_repository`, `core.performance_attribution_repository.PerformanceAttributionRepository`, `core.platform_raw_metrics_repository`, `core.platform_raw_metrics_repository.PlatformRawMetricsRepository`, `core.publish_result_metrics_bridge`, `core.publish_result_metrics_bridge.PublishResultMetricsBridge`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_music_application_builder_channel_guard_smoke.py` | VERWAIST | `core.music_application_builder`, `core.music_application_builder.MusicApplicationBuilder` |
| `test_music_application_builder_smoke.py` | VERWAIST | `core.music_application_builder`, `core.music_application_builder.MusicApplicationBuilder` |
| `test_music_application_models_smoke.py` | LEBEND |  |
| `test_music_application_plan_repository_smoke.py` | VERWAIST | `core.music_application_plan_repository`, `core.music_application_plan_repository.MusicApplicationPlanRepository` |
| `test_music_apply_processor_partial_apply_smoke.py` | VERWAIST | `core.music_apply_processor`, `core.music_apply_processor.MusicApplyProcessor` |
| `test_music_apply_processor_smoke.py` | VERWAIST | `core.music_apply_processor`, `core.music_apply_processor.MusicApplyProcessor` |
| `test_music_apply_timeline_models_smoke.py` | LEBEND |  |
| `test_music_apply_timeline_repository_smoke.py` | VERWAIST | `core.music_apply_timeline_repository`, `core.music_apply_timeline_repository.MusicApplyTimelineRepository` |
| `test_music_apply_timeline_resolver_smoke.py` | VERWAIST | `core.music_apply_timeline_resolver`, `core.music_apply_timeline_resolver.MusicApplyTimelineResolver` |
| `test_music_channel_policy_smoke.py` | VERWAIST | `app`, `app.is_music_intelligence_enabled_for_channel` |
| `test_music_cue_engine_smoke.py` | VERWAIST | `core.music_cue_engine`, `core.music_cue_engine.MusicCueEngine` |
| `test_music_cue_plan_repository_smoke.py` | VERWAIST | `core.music_cue_plan_repository`, `core.music_cue_plan_repository.MusicCuePlanRepository` |
| `test_operations_access_policy_smoke.py` | VERWAIST | `core.operations_dashboard_service`, `core.operations_dashboard_service.OperationsDashboardService` |
| `test_operations_dashboard_service_smoke.py` | VERWAIST | `core.operations_dashboard_service`, `core.operations_dashboard_service.OperationsDashboardService`, `core.queue_store`, `core.queue_store.QueueStore`, `models.queue_entry.QueueEntry`, `shared.opportunity_enums`, `shared.opportunity_enums.OpportunityLevel`, `shared.opportunity_review_enums`, `shared.opportunity_review_enums.OpportunityReviewStatus`, `shared.queue_enums`, `shared.queue_enums.QueueState`, `shared.trend_qualification_enums`, `shared.trend_qualification_enums.LifespanClass` |
| `test_opportunity_review_smoke.py` | VERWAIST | `core.opportunity_review_manager`, `core.opportunity_review_manager.OpportunityReviewManager`, `core.opportunity_review_store`, `core.opportunity_review_store.OpportunityReviewStore`, `core.opportunity_store`, `core.opportunity_store.OpportunityStore`, `core.trend_qualification_store`, `core.trend_qualification_store.TrendQualificationStore`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_opportunity_smoke.py` | VERWAIST | `core.opportunity_manager`, `core.opportunity_manager.OpportunityManager`, `core.opportunity_store`, `core.opportunity_store.OpportunityStore`, `core.trend_qualification_store`, `core.trend_qualification_store.TrendQualificationStore`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_performance_attribution_smoke.py` | VERWAIST | `core.metrics_attribution_bridge`, `core.metrics_attribution_bridge.MetricsAttributionBridge`, `core.normalized_metrics_repository`, `core.normalized_metrics_repository.NormalizedMetricsRepository`, `core.performance_attribution_repository`, `core.performance_attribution_repository.PerformanceAttributionRepository`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_platform_policy_resolver_smoke.py` | VERWAIST | `core.platform_policy_resolver`, `core.platform_policy_resolver.PlatformPolicyResolver` |
| `test_process_gaming_channel_dynamic_plan_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_highlight_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_local_music_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.local_music_selection_repository`, `core.local_music_selection_repository.LocalMusicSelectionRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_longform_timeline_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_music_application_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.music_application_plan_repository`, `core.music_application_plan_repository.MusicApplicationPlanRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_music_apply_partial_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.music_apply_timeline_repository`, `core.music_apply_timeline_repository.MusicApplyTimelineRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_music_apply_timeline_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.music_apply_timeline_repository`, `core.music_apply_timeline_repository.MusicApplyTimelineRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_music_cue_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.music_cue_plan_repository`, `core.music_cue_plan_repository.MusicCuePlanRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_process_gaming_channel_reframe_export_smoke.py` | VERWAIST | `app`, `app.process_gaming_channel`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_publish_guard_real_smoke.py` | VERWAIST | `core.content_variant_repository`, `core.content_variant_repository.ContentVariantRepository`, `core.publish_guard`, `core.publish_guard.PublishGuard`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_publish_package_builder_platform_smoke.py` | VERWAIST | `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_publish_package_builder_source_video_smoke.py` | VERWAIST | `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_publish_result_metrics_bridge_smoke.py` | VERWAIST | `core.normalized_metrics_repository`, `core.normalized_metrics_repository.NormalizedMetricsRepository`, `core.platform_raw_metrics_repository`, `core.platform_raw_metrics_repository.PlatformRawMetricsRepository`, `core.publish_result_metrics_bridge`, `core.publish_result_metrics_bridge.PublishResultMetricsBridge`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_publish_result_variant_binding_smoke.py` | VERWAIST | `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository` |
| `test_publisher_platform_policy_smoke.py` | VERWAIST | `core.publisher`, `core.publisher.Publisher` |
| `test_publisher_worker_guard_flow_smoke.py` | VERWAIST | `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_guard_repository`, `core.publish_guard_repository.PublishGuardRepository`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository`, `publisher_worker` |
| `test_publisher_worker_main_results_file_smoke.py` | VERWAIST | `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository`, `publisher_worker` |
| `test_publisher_worker_orchestrator_variant_smoke.py` | VERWAIST | `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository`, `publisher_worker` |
| `test_publisher_worker_platform_flow_smoke.py` | VERWAIST | `publisher_worker`, `publisher_worker.build_publish_packages_from_job_data`, `publisher_worker.summarize_publish_results` |
| `test_publisher_worker_runtime_gate_smoke.py` | VERWAIST | `core.runtime_mode_controller.RuntimeModeController`, `publisher_worker`, `publisher_worker.is_runtime_action_allowed`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction`, `shared.runtime_modes.RuntimeMode` |
| `test_publisher_worker_short_results_file_smoke.py` | VERWAIST | `core.cross_platform_publish_orchestrator`, `core.cross_platform_publish_orchestrator.CrossPlatformPublishOrchestrator`, `core.publish_result_repository`, `core.publish_result_repository.PublishResultRepository`, `publisher_worker` |
| `test_publisher_worker_storage_provider_smoke.py` | VERWAIST | `publisher_worker` |
| `test_publisher_worker_vacation_gate_smoke.py` | VERWAIST | `publisher_worker`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction` |
| `test_queue_collision_detector_smoke.py` | VERWAIST | `core.queue_collision_detector`, `core.queue_collision_detector.QueueCollisionDetector`, `models.queue_entry.QueueEntry` |
| `test_queue_collision_real_smoke.py` | VERWAIST | `core.queue_collision_snapshot_builder`, `core.queue_collision_snapshot_builder.QueueCollisionSnapshotBuilder`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_collision_resolver_real_smoke.py` | VERWAIST | `core.queue_collision_resolver`, `core.queue_collision_resolver.QueueCollisionResolver`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_collision_resolver_smoke.py` | VERWAIST | `core.queue_collision_resolver`, `core.queue_collision_resolver.QueueCollisionResolver`, `models.queue_entry.QueueEntry` |
| `test_queue_collision_snapshot_builder_smoke.py` | VERWAIST | `core.queue_collision_snapshot_builder`, `core.queue_collision_snapshot_builder.QueueCollisionSnapshotBuilder`, `models.queue_entry.QueueEntry` |
| `test_queue_priority_explainer_real_smoke.py` | VERWAIST | `core.queue_priority_explainer`, `core.queue_priority_explainer.QueuePriorityExplainer`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_priority_explainer_smoke.py` | VERWAIST | `core.queue_priority_explainer`, `core.queue_priority_explainer.QueuePriorityExplainer`, `models.queue_entry.QueueEntry` |
| `test_queue_priority_real_smoke.py` | VERWAIST | `core.queue_priority_manager`, `core.queue_priority_manager.QueuePriorityManager`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_priority_smoke.py` | VERWAIST | `core.queue_priority_manager`, `core.queue_priority_manager.QueuePriorityManager`, `models.queue_entry.QueueEntry` |
| `test_queue_priority_snapshot_builder_smoke.py` | VERWAIST | `core.queue_priority_snapshot_builder`, `core.queue_priority_snapshot_builder.QueuePrioritySnapshotBuilder`, `models.queue_entry.QueueEntry` |
| `test_queue_priority_snapshot_real_smoke.py` | VERWAIST | `core.queue_priority_snapshot_builder`, `core.queue_priority_snapshot_builder.QueuePrioritySnapshotBuilder`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_real_smoke.py` | VERWAIST | `core.opportunity_review_store`, `core.opportunity_review_store.OpportunityReviewStore`, `core.queue_orchestrator`, `core.queue_orchestrator.QueueOrchestrator`, `core.queue_store`, `core.queue_store.QueueStore` |
| `test_queue_smoke.py` | VERWAIST | `core.opportunity_review_store`, `core.opportunity_review_store.OpportunityReviewStore`, `core.queue_orchestrator`, `core.queue_orchestrator.QueueOrchestrator`, `core.queue_store`, `core.queue_store.QueueStore`, `models.opportunity_review_view.OpportunityReviewView`, `shared.opportunity_review_enums`, `shared.opportunity_review_enums.OpportunityReviewStatus`, `shared.queue_enums`, `shared.queue_enums.QueueState` |
| `test_reaction_moment_detector_smoke.py` | LEBEND |  |
| `test_recovery_executor_smoke.py` | VERWAIST | `core.integrity_scanner`, `core.integrity_scanner.IntegrityScanResult`, `core.recovery_executor`, `core.recovery_executor.RecoveryExecutor`, `core.recovery_planner`, `core.recovery_planner.RecoveryPlanner` |
| `test_recovery_planner_smoke.py` | VERWAIST | `core.integrity_scanner`, `core.integrity_scanner.IntegrityScanResult`, `core.recovery_planner`, `core.recovery_planner.RecoveryPlanner` |
| `test_reframe_models_smoke.py` | LEBEND |  |
| `test_reframe_plan_repository_smoke.py` | LEBEND |  |
| `test_reframing_core_smoke.py` | LEBEND |  |
| `test_render_processor_final_package_smoke.py` | LEBEND |  |
| `test_render_processor_music_application_context_smoke.py` | LEBEND |  |
| `test_rerender_worker_dedup_smoke.py` | VERWAIST | `rerender_worker` |
| `test_rerender_worker_runtime_gate_smoke.py` | VERWAIST | `core.runtime_mode_controller.RuntimeModeController`, `rerender_worker`, `rerender_worker.is_runtime_action_allowed`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction`, `shared.runtime_modes.RuntimeMode` |
| `test_rerender_worker_storage_provider_smoke.py` | VERWAIST | `core.runtime_mode_controller.RuntimeModeController`, `rerender_worker` |
| `test_rerender_worker_vacation_gate_smoke.py` | VERWAIST | `rerender_worker`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction` |
| `test_retention_planner_smoke.py` | VERWAIST | `core.retention_planner`, `core.retention_planner.RetentionPlanner` |
| `test_run_gaming_pipeline_dynamic_plan_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_final_render_consumption_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_highlight_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_local_music_main_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_longform_timeline_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_application_main_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_application_render_consumption_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_apply_main_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_apply_partial_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_apply_timeline_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.local_music_catalog_repository`, `core.local_music_catalog_repository.LocalMusicCatalogRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_music_cue_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_reframe_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_run_gaming_pipeline_uncut_music_disabled_smoke.py` | VERWAIST | `app`, `app.run_gaming_pipeline_for_job`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_runtime_mode_controller_smoke.py` | VERWAIST | `core.runtime_mode_controller.RuntimeModeController`, `shared.runtime_modes`, `shared.runtime_modes.RuntimeAction`, `shared.runtime_modes.RuntimeMode` |
| `test_save_pipeline_result_variants_smoke.py` | VERWAIST | `app`, `app.save_pipeline_result`, `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.content_variant_repository`, `core.content_variant_repository.ContentVariantRepository`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_scheduling_policy_evaluator_smoke.py` | VERWAIST | `core.scheduling_policy_evaluator`, `core.scheduling_policy_evaluator.SchedulingPolicyEvaluator`, `core.scheduling_policy_manager`, `core.scheduling_policy_manager.SchedulingPolicyManager`, `core.scheduling_policy_store`, `core.scheduling_policy_store.SchedulingPolicyStore`, `models.queue_entry.QueueEntry` |
| `test_scheduling_policy_real_smoke.py` | VERWAIST | `core.queue_store`, `core.queue_store.QueueStore`, `core.scheduling_policy_evaluator`, `core.scheduling_policy_evaluator.SchedulingPolicyEvaluator`, `core.scheduling_policy_manager`, `core.scheduling_policy_manager.SchedulingPolicyManager`, `core.scheduling_policy_store`, `core.scheduling_policy_store.SchedulingPolicyStore` |
| `test_scheduling_policy_smoke.py` | VERWAIST | `core.scheduling_policy_manager`, `core.scheduling_policy_manager.SchedulingPolicyManager`, `core.scheduling_policy_store`, `core.scheduling_policy_store.SchedulingPolicyStore` |
| `test_scheduling_time_real_smoke.py` | VERWAIST | `core.queue_store`, `core.queue_store.QueueStore`, `core.scheduling_policy_manager`, `core.scheduling_policy_manager.SchedulingPolicyManager`, `core.scheduling_policy_store`, `core.scheduling_policy_store.SchedulingPolicyStore`, `core.scheduling_time_resolver`, `core.scheduling_time_resolver.SchedulingTimeResolver` |
| `test_scheduling_time_resolver_smoke.py` | VERWAIST | `core.scheduling_time_resolver`, `core.scheduling_time_resolver.SchedulingTimeResolver` |
| `test_shorts_generator_uses_raw_source_smoke.py` | VERWAIST | `core.shorts_generator`, `core.shorts_generator.ShortsGenerator` |
| `test_tiktok_uploader_smoke.py` | VERWAIST | `core.publisher`, `core.publisher.Publisher`, `core.tiktok_uploader`, `core.tiktok_uploader.TikTokUploadError`, `core.tiktok_uploader.TikTokUploader`, `core.tiktok_uploader._STATUS_MAX_POLLS`, `core.tiktok_uploader._build_caption`, `core.tiktok_uploader._chunk_size_for` |
| `test_trend_qualification_smoke.py` | VERWAIST | `core.trend_qualification_manager`, `core.trend_qualification_manager.TrendQualificationManager`, `core.trend_qualification_store`, `core.trend_qualification_store.TrendQualificationStore`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_trend_smoke.py` | VERWAIST | `core.trend_intake_manager`, `core.trend_intake_manager.TrendIntakeManager`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_unified_metrics_layer_smoke.py` | VERWAIST | `core.metrics_sync_manager`, `core.metrics_sync_manager.MetricsSyncManager`, `core.normalized_metrics_repository`, `core.normalized_metrics_repository.NormalizedMetricsRepository`, `core.platform_raw_metrics_repository`, `core.platform_raw_metrics_repository.PlatformRawMetricsRepository` |
| `test_vacation_controller_smoke.py` | LEBEND |  |
| `test_variant_to_publish_package_smoke.py` | VERWAIST | `core.content_variant_builder`, `core.content_variant_builder.ContentVariantBuilder`, `core.publish_package_builder`, `core.publish_package_builder.PublishPackageBuilder` |
| `test_vertical_reframe_engine_smoke.py` | VERWAIST | `core.shorts_decision_engine`, `core.shorts_decision_engine.ShortsDecisionEngine`, `core.vertical_reframe_engine`, `core.vertical_reframe_engine.VerticalReframeEngine` |
| `test_workspace_repository_smoke.py` | VERWAIST | `core.workspace_repository`, `core.workspace_repository.WorkspaceRepository`, `models.workspace_membership.WorkspaceMembership`, `shared.role_enums`, `shared.role_enums.RoleType` |
| `test_youtube_live_connector_smoke.py` | VERWAIST | `core.connectors.youtube_most_popular_connector`, `core.connectors.youtube_most_popular_connector.YouTubeMostPopularConnector`, `core.live_trend_intake_runner`, `core.live_trend_intake_runner.LiveTrendIntakeRunner`, `core.trend_intake_manager`, `core.trend_intake_manager.TrendIntakeManager`, `core.trend_store`, `core.trend_store.TrendStore` |
| `test_zoom_pacing_engine_smoke.py` | LEBEND |  |

## Phase 1.5b Finding: ffmpeg Render Integration

- 	est_final_render_driver_smoke.py enthält 3 echte ffmpeg-/moviepy-Render-Integrationstests.
- Befund: Diese Tests machen echtes Rendering über FinalRenderDriver().render().
- Bekannter technischer Befund: hartkodierter ffmpeg-Pfad D:\Tools\ffmpeg\bin\ffmpeg.exe in der Render-Kette.
- Auf dieser Maschine wurde sichtbar: Render gibt None zurück und erzeugt TypeError: cannot unpack non-iterable NoneType object.
- Nicht in Phase 1 gefixt. Das ist ein Phase-2-Befund für Render-/ffmpeg-Konsolidierung.
- Die 3 Tests bleiben im Repo, werden mit @pytest.mark.ffmpeg_integration markiert und im Standardlauf per ddopts = -m "not ffmpeg_integration" ausgeschlossen.
