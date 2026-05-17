# PROJECT ZENITH — PHASE 1 CLEANUP LIST

## Status

Aktueller HEAD:

```text
ede6124dd8c4fb2c82ecd406d777a2acbcdf73e1 feat(P1-4): add asset folder structure and asset paths module
```

- Cleanup 1.5 wurde noch nicht ausgefuehrt.
- Diese Datei ist nur die Pruef- und Entscheidungsliste.
- _patch_ und _verify_ sind lokal vorhanden, aber nicht als Git-HEAD-Dateien getrackt.
- git ls-files Treffer fuer _patch_ oder _verify_: 0

## A) Zum Verschieben

| Datei | Ziel | Kollision in tests/? ja/nein | Git-getrackt? ja/nein | Grund | Entscheidung |
|---|---|---|---|---|---|
| test_access_context_service_smoke.py | tests/test_access_context_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_app_runtime_gate_smoke.py | tests/test_app_runtime_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_app_vacation_gate_smoke.py | tests/test_app_vacation_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_audio_cue_models_smoke.py | tests/test_audio_cue_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_audio_mix_planner_smoke.py | tests/test_audio_mix_planner_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_authorization_service_smoke.py | tests/test_authorization_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_content_variant_builder_repository_smoke.py | tests/test_content_variant_builder_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_cross_platform_publish_guard_smoke.py | tests/test_cross_platform_publish_guard_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_cross_platform_publish_orchestrator_smoke.py | tests/test_cross_platform_publish_orchestrator_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_access_context_surface_smoke.py | tests/test_dashboard_access_context_surface_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_command_deck_smoke.py | tests/test_dashboard_command_deck_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_feedback_surface_render_smoke.py | tests/test_dashboard_feedback_surface_render_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_full_operations_layout_smoke.py | tests/test_dashboard_full_operations_layout_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_high_tech_layout_smoke.py | tests/test_dashboard_high_tech_layout_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_high_tech_presence_smoke.py | tests/test_dashboard_high_tech_presence_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_jarvis_panel_smoke.py | tests/test_dashboard_jarvis_panel_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_kpi_surface_render_smoke.py | tests/test_dashboard_kpi_surface_render_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_role_guard_smoke.py | tests/test_dashboard_role_guard_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_roles_permissions_surface_smoke.py | tests/test_dashboard_roles_permissions_surface_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_runtime_gate_smoke.py | tests/test_dashboard_runtime_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_storage_provider_mutation_smoke.py | tests/test_dashboard_storage_provider_mutation_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_storage_provider_smoke.py | tests/test_dashboard_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_unified_operations_surface_smoke.py | tests/test_dashboard_unified_operations_surface_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_vacation_gate_smoke.py | tests/test_dashboard_vacation_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dashboard_vacation_smoke.py | tests/test_dashboard_vacation_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dynamic_edit_models_smoke.py | tests/test_dynamic_edit_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_dynamic_edit_plan_repository_smoke.py | tests/test_dynamic_edit_plan_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_edit_signal_extractor_smoke.py | tests/test_edit_signal_extractor_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_edit_timeline_models_smoke.py | tests/test_edit_timeline_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_edit_timeline_repository_smoke.py | tests/test_edit_timeline_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_energy_curve_builder_smoke.py | tests/test_energy_curve_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_export_manager_storage_provider_smoke.py | tests/test_export_manager_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_facecam_gameplay_separator_smoke.py | tests/test_facecam_gameplay_separator_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_faceless_pipeline_smoke.py | tests/test_faceless_pipeline_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_feedback_context_bridge_smoke.py | tests/test_feedback_context_bridge_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_feedback_dashboard_service_smoke.py | tests/test_feedback_dashboard_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_feedback_learning_backbone_smoke.py | tests/test_feedback_learning_backbone_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_final_edit_integration_smoke.py | tests/test_final_edit_integration_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_final_render_driver_smoke.py | tests/test_final_render_driver_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_finalize_pipeline_result_variants_smoke.py | tests/test_finalize_pipeline_result_variants_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_google_trends_rss_smoke.py | tests/test_google_trends_rss_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_highlight.py | tests/test_highlight.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_highlight_candidate_repository_smoke.py | tests/test_highlight_candidate_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_highlight_selector_smoke.py | tests/test_highlight_selector_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_highlight_selector_weak_zone_smoke.py | tests/test_highlight_selector_weak_zone_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_import.py | tests/test_import.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_integrity_scanner_smoke.py | tests/test_integrity_scanner_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_blocked_warning_publish_smoke.py | tests/test_jarvis_blocked_warning_publish_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_command_parser_smoke.py | tests/test_jarvis_command_parser_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_command_service_smoke.py | tests/test_jarvis_command_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_presence_service_smoke.py | tests/test_jarvis_presence_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_queue_maintenance_smoke.py | tests/test_jarvis_queue_maintenance_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_jarvis_status_service_smoke.py | tests/test_jarvis_status_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_job_loader_storage_provider_smoke.py | tests/test_job_loader_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_job_repository_storage_provider_smoke.py | tests/test_job_repository_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_job_store_storage_provider_smoke.py | tests/test_job_store_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_kpi_dashboard_service_smoke.py | tests/test_kpi_dashboard_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_kpi_insight_surface_smoke.py | tests/test_kpi_insight_surface_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_local_music_catalog_repository_smoke.py | tests/test_local_music_catalog_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_local_music_selection_repository_smoke.py | tests/test_local_music_selection_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_local_music_selector_channel_guard_smoke.py | tests/test_local_music_selector_channel_guard_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_local_music_selector_reuse_guard_smoke.py | tests/test_local_music_selector_reuse_guard_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_local_music_selector_smoke.py | tests/test_local_music_selector_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_longform_timeline_builder_smoke.py | tests/test_longform_timeline_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_maintenance_report_builder_smoke.py | tests/test_maintenance_report_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_maintenance_runner_smoke.py | tests/test_maintenance_runner_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_metrics_to_attribution_chain_smoke.py | tests/test_metrics_to_attribution_chain_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_application_builder_channel_guard_smoke.py | tests/test_music_application_builder_channel_guard_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_application_builder_smoke.py | tests/test_music_application_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_application_models_smoke.py | tests/test_music_application_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_application_plan_repository_smoke.py | tests/test_music_application_plan_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_apply_processor_partial_apply_smoke.py | tests/test_music_apply_processor_partial_apply_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_apply_processor_smoke.py | tests/test_music_apply_processor_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_apply_timeline_models_smoke.py | tests/test_music_apply_timeline_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_apply_timeline_repository_smoke.py | tests/test_music_apply_timeline_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_apply_timeline_resolver_smoke.py | tests/test_music_apply_timeline_resolver_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_channel_policy_smoke.py | tests/test_music_channel_policy_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_cue_engine_smoke.py | tests/test_music_cue_engine_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_music_cue_plan_repository_smoke.py | tests/test_music_cue_plan_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_operations_access_policy_smoke.py | tests/test_operations_access_policy_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_operations_dashboard_service_smoke.py | tests/test_operations_dashboard_service_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_opportunity_review_smoke.py | tests/test_opportunity_review_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_opportunity_smoke.py | tests/test_opportunity_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_performance_attribution_smoke.py | tests/test_performance_attribution_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_platform_policy_resolver_smoke.py | tests/test_platform_policy_resolver_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_dynamic_plan_export_smoke.py | tests/test_process_gaming_channel_dynamic_plan_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_highlight_export_smoke.py | tests/test_process_gaming_channel_highlight_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_local_music_export_smoke.py | tests/test_process_gaming_channel_local_music_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_longform_timeline_export_smoke.py | tests/test_process_gaming_channel_longform_timeline_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_music_application_export_smoke.py | tests/test_process_gaming_channel_music_application_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_music_apply_partial_export_smoke.py | tests/test_process_gaming_channel_music_apply_partial_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_music_apply_timeline_export_smoke.py | tests/test_process_gaming_channel_music_apply_timeline_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_music_cue_export_smoke.py | tests/test_process_gaming_channel_music_cue_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_process_gaming_channel_reframe_export_smoke.py | tests/test_process_gaming_channel_reframe_export_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publish_guard_real_smoke.py | tests/test_publish_guard_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publish_package_builder_platform_smoke.py | tests/test_publish_package_builder_platform_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publish_package_builder_source_video_smoke.py | tests/test_publish_package_builder_source_video_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publish_result_metrics_bridge_smoke.py | tests/test_publish_result_metrics_bridge_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publish_result_variant_binding_smoke.py | tests/test_publish_result_variant_binding_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_platform_policy_smoke.py | tests/test_publisher_platform_policy_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_guard_flow_smoke.py | tests/test_publisher_worker_guard_flow_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_main_results_file_smoke.py | tests/test_publisher_worker_main_results_file_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_orchestrator_variant_smoke.py | tests/test_publisher_worker_orchestrator_variant_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_platform_flow_smoke.py | tests/test_publisher_worker_platform_flow_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_runtime_gate_smoke.py | tests/test_publisher_worker_runtime_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_short_results_file_smoke.py | tests/test_publisher_worker_short_results_file_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_storage_provider_smoke.py | tests/test_publisher_worker_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_publisher_worker_vacation_gate_smoke.py | tests/test_publisher_worker_vacation_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_collision_detector_smoke.py | tests/test_queue_collision_detector_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_collision_real_smoke.py | tests/test_queue_collision_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_collision_resolver_real_smoke.py | tests/test_queue_collision_resolver_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_collision_resolver_smoke.py | tests/test_queue_collision_resolver_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_collision_snapshot_builder_smoke.py | tests/test_queue_collision_snapshot_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_explainer_real_smoke.py | tests/test_queue_priority_explainer_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_explainer_smoke.py | tests/test_queue_priority_explainer_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_real_smoke.py | tests/test_queue_priority_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_smoke.py | tests/test_queue_priority_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_snapshot_builder_smoke.py | tests/test_queue_priority_snapshot_builder_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_priority_snapshot_real_smoke.py | tests/test_queue_priority_snapshot_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_real_smoke.py | tests/test_queue_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_queue_smoke.py | tests/test_queue_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_reaction_moment_detector_smoke.py | tests/test_reaction_moment_detector_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_recovery_executor_smoke.py | tests/test_recovery_executor_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_recovery_planner_smoke.py | tests/test_recovery_planner_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_reframe_models_smoke.py | tests/test_reframe_models_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_reframe_plan_repository_smoke.py | tests/test_reframe_plan_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_reframing_core_smoke.py | tests/test_reframing_core_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_render_processor_final_package_smoke.py | tests/test_render_processor_final_package_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_render_processor_music_application_context_smoke.py | tests/test_render_processor_music_application_context_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_rerender_worker_dedup_smoke.py | tests/test_rerender_worker_dedup_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_rerender_worker_runtime_gate_smoke.py | tests/test_rerender_worker_runtime_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_rerender_worker_storage_provider_smoke.py | tests/test_rerender_worker_storage_provider_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_rerender_worker_vacation_gate_smoke.py | tests/test_rerender_worker_vacation_gate_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_retention_planner_smoke.py | tests/test_retention_planner_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_dynamic_plan_smoke.py | tests/test_run_gaming_pipeline_dynamic_plan_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_final_render_consumption_smoke.py | tests/test_run_gaming_pipeline_final_render_consumption_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_highlight_smoke.py | tests/test_run_gaming_pipeline_highlight_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_local_music_main_smoke.py | tests/test_run_gaming_pipeline_local_music_main_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_longform_timeline_smoke.py | tests/test_run_gaming_pipeline_longform_timeline_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_application_main_smoke.py | tests/test_run_gaming_pipeline_music_application_main_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_application_render_consumption_smoke.py | tests/test_run_gaming_pipeline_music_application_render_consumption_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_apply_main_smoke.py | tests/test_run_gaming_pipeline_music_apply_main_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_apply_partial_smoke.py | tests/test_run_gaming_pipeline_music_apply_partial_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_apply_timeline_smoke.py | tests/test_run_gaming_pipeline_music_apply_timeline_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_music_cue_smoke.py | tests/test_run_gaming_pipeline_music_cue_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_reframe_smoke.py | tests/test_run_gaming_pipeline_reframe_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_run_gaming_pipeline_uncut_music_disabled_smoke.py | tests/test_run_gaming_pipeline_uncut_music_disabled_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_runtime_mode_controller_smoke.py | tests/test_runtime_mode_controller_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_save_pipeline_result_variants_smoke.py | tests/test_save_pipeline_result_variants_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_scheduling_policy_evaluator_smoke.py | tests/test_scheduling_policy_evaluator_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_scheduling_policy_real_smoke.py | tests/test_scheduling_policy_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_scheduling_policy_smoke.py | tests/test_scheduling_policy_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_scheduling_time_real_smoke.py | tests/test_scheduling_time_real_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_scheduling_time_resolver_smoke.py | tests/test_scheduling_time_resolver_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_shorts_generator_uses_raw_source_smoke.py | tests/test_shorts_generator_uses_raw_source_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_tiktok_uploader_smoke.py | tests/test_tiktok_uploader_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_trend_qualification_smoke.py | tests/test_trend_qualification_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_trend_smoke.py | tests/test_trend_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_unified_metrics_layer_smoke.py | tests/test_unified_metrics_layer_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_vacation_controller_smoke.py | tests/test_vacation_controller_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_variant_to_publish_package_smoke.py | tests/test_variant_to_publish_package_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_vertical_reframe_engine_smoke.py | tests/test_vertical_reframe_engine_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_workspace_repository_smoke.py | tests/test_workspace_repository_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_youtube_live_connector_smoke.py | tests/test_youtube_live_connector_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| test_zoom_pacing_engine_smoke.py | tests/test_zoom_pacing_engine_smoke.py | nein | ja | Root-Test gehoert nicht in Root | verschieben nach tests/ |
| BUG_DIAGNOSIS.md | docs/archive/BUG_DIAGNOSIS.md | nein | ja | Root-Markdown/Analyse-Doku gehoert nicht in Root | verschieben nach docs/archive/ |
| PROJECT_INVENTORY.md | docs/archive/PROJECT_INVENTORY.md | nein | ja | Root-Markdown/Analyse-Doku gehoert nicht in Root | verschieben nach docs/archive/ |
| ZENITH_PHASE_2B_PRO_ANALYSIS.md | docs/archive/ZENITH_PHASE_2B_PRO_ANALYSIS.md | nein | ja | Root-Markdown/Analyse-Doku gehoert nicht in Root | verschieben nach docs/archive/ |
| rreset_jobs.py | scripts/rreset_jobs.py | nein | ja | Hilfsskript gehoert nicht in Root | verschieben nach scripts/ |
| rreset_all_jobs.py | scripts/rreset_all_jobs.py | nein | ja | Hilfsskript gehoert nicht in Root | verschieben nach scripts/ |

## B) Zum Loeschen

| Datei | Art | Git-getrackt? ja/nein | HEAD-Bewertung | Entscheidung |
|---|---|---|---|---|
| _audit_all_2b_markers.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_approval_flow_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_audio_artifacts_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_coverage.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_coverage_install.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_coverage_pytest.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_dead_module_samples.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_e2e_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_final_audit_files.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_gaming_pipeline_2b_markers.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_gaming_pipeline_calls_grep.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_gaming_pipeline_imports.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_initial_repro.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_post_fix_repro.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_pytest_full.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_pytest_mark_usage.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_pytest_markers.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_pytest_skips.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_repo_inventory.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_review_only_flags.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_review_only_tests.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_review_only_true_flags.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_sentence_boundary_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_signal_path_summary.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_signal_registry_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_synthetic_ffmpeg_create.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_synthetic_post_fix_cli.log | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_test_sample_classification.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_test_sample_files.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_unique_2b_markers.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _audit_whisper_search.txt | lokales Audit-Artefakt | ja | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c1_status_consistency.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c2b_compact_gate.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c2b_global_override.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c2b_microfix_job_attr.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c2b_mini_override_log.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c2b_render_gate.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _patch_2c3b_real_probe_test.py | lokales Patch-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c0_diff_review.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_coverage.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_create_synth.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_create_synth.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_diff_audit_before_commit.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_inventory_before.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_jobs_before_delete.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_old_job_before_delete.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_real_run.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_real_run_second_synth.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c1_remove_old_job.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2a_inventory.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_approved_final_audit_material.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_approved_stop_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_block8_field_inventory.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_block8_field_table_compact.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_block8_values_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_compact_recovery_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_coverage_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_create_auto_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_create_noapprove_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_create_synth_final.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_decision_detail.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_diag_create_synth.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_diag_create_synth.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_diag_run.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_diff_audit_before_commit.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_extract_decision.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_global_override_audit_material.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_global_override_stop_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_microfix_after_gaming_pipeline.diff | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_microfix_before_gaming_pipeline.diff | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_microfix_final_audit_material.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_microfix_stop_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_pytest_corrected.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_pytest_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_pytest_microfix.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_recovery_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_run_autoapprove_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_run_noapprove_final.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c2b_summarize_detail.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3a_whisper_inventory.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_correction_report.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_direct_probe.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_direct_probe.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_ffmpeg_convert.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_fixture_test_only.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_locate_ffmpeg.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_readonly_evidence_report.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_readonly_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_readonly_sentence_boundary.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_sentence_boundary_check.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_sentence_boundary_check.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_sentence_boundary_probe.json | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_sentence_boundary_probe.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_stop_diag.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c3b_whisper_probe_report.txt | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c4_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c5_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_2c6_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_create_synth_2c0.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_create_synth_2c0.py | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_pytest.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |
| _verify_real_run.log | lokales Verify-Artefakt | nein | nicht als HEAD-Loeschung behandeln | nur nach JA CLEANUP 1.5 lokal loeschen |

## C) Behalten / Unklar

| Datei / Muster | Vorschlag | Grund |
|---|---|---|
| assets/sfx/censor/censor_sfx_manifest.json | behalten | bestehendes Manifest; darf nicht geloescht werden |
| assets/README.md | behalten | Phase-1 Asset-Doku |
| core/asset_paths.py | behalten | Phase-1 Asset-Pfadmodul |
| docs/PHASE1_CLEANUP_LIST.md | behalten | diese Pruefliste |
| pytest-cache-files-* | unklar / nicht anfassen | Permission-Warnungen; nicht Teil dieses Cleanups |
| Lokale untracked Dateien `_patch_*`, `_verify_*` | nicht im Repo, nicht anfassen | nicht im Repo, nicht angefasst, vom Nutzer lokal manuell zu prüfen |

## STOPP-PUNKT

Nichts loeschen.
Nichts verschieben.
Cleanup 1.5 erst nach ausdruecklichem JA CLEANUP 1.5.

## Ergebnis Unterphase 1.5

Ausgeführt und committed:

- BUG_DIAGNOSIS.md -> docs/archive/BUG_DIAGNOSIS.md
- PROJECT_INVENTORY.md -> docs/archive/PROJECT_INVENTORY.md
- ZENITH_PHASE_2B_PRO_ANALYSIS.md -> docs/archive/ZENITH_PHASE_2B_PRO_ANALYSIS.md
reset_jobs.py -> scripts/rreset_jobs.py
reset_all_jobs.py -> scripts/rreset_all_jobs.py

Nicht ausgeführt:

- Root-	est_*.py Dateien wurden nicht dauerhaft nach 	ests/ verschoben.

Grund:

- Der Move der 165 Root-Tests nach 	ests/ hat die Pytest-Sammlung aktiviert und 135 Collection-Errors ausgelöst.
- Nach Rollback der Root-Test-Moves war der Testlauf wieder grün: 3493 passed, 2 skipped, 2 warnings.
- Root-Test-Move bleibt deshalb Blocker und braucht eine eigene spätere Migrations-Unterphase.

Lokale untracked Dateien:

- _patch_*, _verify_*, _audit_* wurden nicht angefasst.
- Sie sind nicht Teil von HEAD und bleiben lokale Arbeitsartefakte zur manuellen Prüfung durch den Nutzer.
