# PROJECT_INVENTORY — Zenith

Erstellt: 2026-04-28  
Analysiert: `core/` (110 Module), `models/` (55 Dateien), Root-Scripts, 163 Smoke-Tests

---

## 1. Module-Übersicht (`core/`)

**Statusregel:**
- **aktiv genutzt** = direkt in einem der 7 Entry-Points importiert ODER nachweislich über eine aktive Import-Kette erreichbar
- **scheint isoliert** = nur in Tests importiert oder gar nirgends
- **unklar** = nicht abschließend verfolgbar

### 1.1 Intake & Job-Verwaltung

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `intake_manager.py` | Erstellt Jobs aus Inbox-Scans | `job_store` | aktiv genutzt |
| `job_store.py` | JSON-basierte Job-Persistenz | – | aktiv genutzt |
| `job_repository.py` | Job-Abfragen & Filter | – | aktiv genutzt |
| `job_loader.py` | Job-Deserialisierung aus JSON | – | aktiv genutzt |
| `inbox_scanner.py` | Sucht neue MP4s in `inbox/` | – | aktiv genutzt |
| `routing_engine.py` | Weist Jobs dem richtigen Pipeline-Zweig zu | – | aktiv genutzt |
| `export_manager.py` | Exportiert Ergebnisse nach `exports/` | – | aktiv genutzt |
| `validator.py` | Validiert Job vor dem Publish | – | aktiv genutzt |
| `content_classifier.py` | Klassifiziert Content-Typ | – | aktiv genutzt |
| `content_variant_builder.py` | Baut Content-Varianten (16:9, 9:16) | – | aktiv genutzt |
| `content_variant_repository.py` | Persistenz der Content-Varianten | – | aktiv genutzt |

### 1.2 Highlight-Erkennung & Analyse

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `edit_signal_extractor.py` | Frame-für-Frame Signalextraktion (Audio/Motion) | – | aktiv genutzt |
| `highlight_selector.py` | Scoring & Segment-Selektion | – | aktiv genutzt |
| `highlight_candidate_repository.py` | Persistenz der Highlight-Kandidaten | – | aktiv genutzt |
| `gaming_analyzer.py` | Gameplay-Metriken & Motion-Analyse | – | aktiv genutzt |
| `gaming_cutter.py` | Extrahiert Gameplay-Clips | – | aktiv genutzt |

### 1.3 Timeline & Editing

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `longform_timeline_builder.py` | Baut Editing-Timeline (hook/build/payoff) | – | aktiv genutzt |
| `edit_timeline_repository.py` | Persistenz der Editing-Timeline | – | aktiv genutzt |
| `dynamic_edit_plan_repository.py` | Persistenz dynamischer Editpläne | – | aktiv genutzt |
| `final_edit_integration.py` | Konsolidiert alle Editpläne | – | aktiv genutzt |

### 1.4 Musik & Audio

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `music_cue_engine.py` | Erkennt Musik-Cue-Positionen | – | aktiv genutzt |
| `music_cue_plan_repository.py` | Persistenz der Music-Cue-Pläne | – | aktiv genutzt |
| `audio_mix_planner.py` | Plant Audio-Mixing-Strategie | – | aktiv genutzt |
| `music_apply_processor.py` | Wendet Musik auf Timeline an | – | aktiv genutzt |
| `music_application_builder.py` | Baut Music-Application-Plan | – | aktiv genutzt |
| `music_application_plan_repository.py` | Persistenz des Music-Application-Plans | – | aktiv genutzt |
| `local_music_catalog_repository.py` | Lokaler Musik-Asset-Katalog | – | aktiv genutzt |
| `local_music_selection_repository.py` | Persistenz der Musikauswahl | – | aktiv genutzt |
| `local_music_selector.py` | Musikauswahl-Logik (channel-aware) | `local_music_catalog_repository` | aktiv genutzt |
| `music_apply_timeline_resolver.py` | Löst Music-Apply-Timeline auf | `scheduling_gap_resolver` (indirekt, unklar) | aktiv genutzt |
| `music_apply_timeline_repository.py` | Persistenz der Music-Apply-Timeline | – | aktiv genutzt |

### 1.5 Rendering & Video

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `final_render_driver.py` | FFmpeg-Orchestrator, GPU-Encoding (h264\_nvenc) | – | aktiv genutzt |
| `render_processor.py` | Komposition des finalen Pakets | – | aktiv genutzt |
| `reframing_core.py` | Vertikales Reframing (Shorts) | `facecam_gameplay_separator` | aktiv genutzt |
| `vertical_reframe_engine.py` | Dynamisches 16:9→9:16-Reframing | – | aktiv genutzt |
| `reframe_plan_repository.py` | Persistenz des Reframe-Plans | – | aktiv genutzt |
| `facecam_gameplay_separator.py` | OBS 32:9 Facecam-Erkennung | – | aktiv genutzt |
| `director_engine.py` | Auto-Direktor für 32:9-OBS-Aufnahmen | – | **scheint isoliert** |
| `reaction_moment_detector.py` | Erkennt Sprecher-Reaktionen | – | aktiv genutzt |
| `zoom_pacing_engine.py` | Ken-Burns-Zoom-Timing | – | aktiv genutzt |
| `subtitle_processor.py` | SRT/Untertitel-Generierung | – | aktiv genutzt |
| `title_generator.py` | Auto-Titel-Generierung | – | aktiv genutzt |
| `metadata_generator.py` | Video-Metadaten-Zusammenstellung | – | aktiv genutzt |
| `thumbnail_forge.py` | Statische Thumbnail-Generierung | – | aktiv genutzt |
| `ai_thumbnail_forge.py` | KI-gestützte Thumbnail-Generierung | `thumbnail_forge`, `thumbnail_prompt_builder` | aktiv genutzt |
| `thumbnail_prompt_builder.py` | Baut Prompt für KI-Thumbnail | – | aktiv genutzt |

> **Hinweis `director_engine.py`:** Hat einen eigenen `if __name__ == '__main__'`-Block und wird von keinem anderen Modul importiert. Beschreibt sich selbst als "pipeline stage 4", ist aber nie in die aktive Pipeline integriert worden.

### 1.6 Shorts & Reels

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `shorts_decision_engine.py` | Entscheidet, ob Clip Shorts-würdig ist | – | aktiv genutzt |
| `shorts_generator.py` | Generiert Short-Form-Clips | `vertical_reframe_engine` | aktiv genutzt |

### 1.7 Faceless Pipeline

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `faceless_pipeline.py` | Text-to-Video Faceless Content (TTS) | `faceless_brief_builder`, `faceless_asset_builder`, `faceless_assembler` | aktiv genutzt |
| `faceless_brief_builder.py` | Baut Faceless-Content-Brief | – | aktiv genutzt |
| `faceless_asset_builder.py` | Generiert Faceless-Assets | – | aktiv genutzt |
| `faceless_assembler.py` | Assembliert Faceless-Video | – | aktiv genutzt |

### 1.8 Publishing

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `publisher.py` | Upload zu YouTube/TikTok/Instagram | `youtube_uploader`, `tiktok_uploader` (lazy) | aktiv genutzt |
| `youtube_uploader.py` | YouTube-Upload-Handler | – | aktiv genutzt |
| `tiktok_uploader.py` | TikTok-Upload-Handler (423 Zeilen) | – | aktiv genutzt |
| `publish_package_builder.py` | Baut Upload-Payload | – | aktiv genutzt |
| `publish_guard.py` | Pre-Publish-Validierung | – | aktiv genutzt |
| `publish_guard_repository.py` | Persistenz der Guard-Ergebnisse | – | aktiv genutzt |
| `publish_result_repository.py` | Verfolgt Upload-Ergebnisse | – | aktiv genutzt |
| `autopublish_gate.py` | Auto vs. Manual Publish-Entscheidung | – | aktiv genutzt |
| `cross_platform_publish_orchestrator.py` | Multi-Plattform-Dispatch | `publish_guard`, `publish_guard_repository`, `publish_result_repository`, `publisher` | aktiv genutzt |
| `platform_policy_resolver.py` | Plattform-spezifische Richtlinien auflösen | – | aktiv genutzt |
| `scheduler.py` | Plant Publish-Zeitpunkte | – | aktiv genutzt |

### 1.9 Queue & Priorisierung

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `queue_store.py` | Queue-Persistenz | – | aktiv genutzt |
| `queue_orchestrator.py` | Queue-Manager | `queue_store`, `queue_priority_manager` | **scheint isoliert** |
| `queue_priority_manager.py` | Queue-Priorisierungs-Manager | `queue_priority_scorer` | **scheint isoliert** |
| `queue_priority_scorer.py` | Berechnet Queue-Priorität | – | **scheint isoliert** |
| `queue_priority_explainer.py` | Erklärt Priorisierungsentscheidungen | – | **scheint isoliert** |
| `queue_priority_snapshot_builder.py` | Erstellt Prioritäts-Snapshot | `queue_priority_manager` | **scheint isoliert** |
| `queue_collision_detector.py` | Erkennt Queue-Kollisionen | – | **scheint isoliert** |
| `queue_collision_snapshot_builder.py` | Erstellt Kollisions-Snapshot | `queue_collision_detector` | **scheint isoliert** |
| `queue_collision_resolver.py` | Löst Queue-Kollisionen auf | `queue_collision_detector`, `queue_priority_manager` | **scheint isoliert** |

> **Hinweis Queue-Module:** `queue_store` wird aktiv von `jarvis_status_service` genutzt. Die gesamte Priorisierungs- und Kollisions-Schicht (8 Module) ist jedoch nur in Tests importiert – sie sind gebaut, aber nicht in den aktiven Workflow integriert.

### 1.10 Scheduling & Policies

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `scheduling_policy_store.py` | Persistenz von Scheduling-Richtlinien | – | **scheint isoliert** |
| `scheduling_policy_manager.py` | Verwaltet Scheduling-Richtlinien | `scheduling_policy_store` | **scheint isoliert** |
| `scheduling_policy_evaluator.py` | Bewertet Scheduling-Richtlinien | `scheduling_policy_manager` | **scheint isoliert** |
| `scheduling_time_resolver.py` | Löst Publish-Zeiten auf | `scheduling_gap_resolver` | **scheint isoliert** |
| `scheduling_gap_resolver.py` | Findet freie Slots im Schedule | – | **scheint isoliert** |

> **Hinweis:** `scheduler.py` (aktiv genutzt in `app.py`) importiert **keine** dieser Scheduling-Module. Die gesamte Scheduling-Richtlinien-Schicht ist nur in Tests vorhanden.

### 1.11 Trends & Opportunities

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `trend_store.py` | Trend-Persistenz | – | **scheint isoliert** |
| `trend_source_connector.py` | Abstrakte Trend-Daten-Schnittstelle | – | **scheint isoliert** |
| `trend_intake_manager.py` | Trend-Intake-Orchestrierung | `trend_normalizer`, `trend_store` | **scheint isoliert** |
| `trend_normalizer.py` | Normalisiert Trend-Signale | – | **scheint isoliert** |
| `trend_qualifier.py` | Bewertet & qualifiziert Trends | – | **scheint isoliert** |
| `trend_qualification_store.py` | Persistenz qualifizierter Trends | – | **scheint isoliert** |
| `trend_qualification_manager.py` | Manages Trend-Qualifikations-Workflow | `trend_qualifier`, `trend_store` | **scheint isoliert** |
| `live_trend_intake_runner.py` | Führt Live-Trend-Intake durch | `trend_intake_manager`, `trend_source_connector` | **scheint isoliert** |
| `opportunity_store.py` | Opportunity-Persistenz | – | **scheint isoliert** |
| `opportunity_scorer.py` | Bewertet Opportunities (349 Zeilen) | – | **scheint isoliert** |
| `opportunity_manager.py` | Erstellt Opportunities aus Trends | `opportunity_scorer`, `trend_store` | **scheint isoliert** |
| `opportunity_review_store.py` | Persistenz von Opportunity-Reviews | – | **scheint isoliert** |
| `opportunity_review_builder.py` | Baut Opportunity-Review-Views | – | **scheint isoliert** |
| `opportunity_review_manager.py` | Manages Opportunity-Review-Workflow | `opportunity_review_store`, `trend_store` | **scheint isoliert** |
| `connectors/google_trends_rss_connector.py` | Google Trends RSS-Ingestion | `trend_source_connector` | **scheint isoliert** |
| `connectors/youtube_most_popular_connector.py` | YouTube Shorts Trending-Daten | `trend_source_connector` | **scheint isoliert** |

> **Hinweis:** Das komplette Trends/Opportunities-Subsystem (14+ Module) ist nur in Tests importiert. Es wurden Daten in `data/trend_signals.json` (71 KB) angesammelt, aber der Workflow ist nie in `app.py`, `dashboard.py` oder `pipeline_runner.py` eingebunden.

### 1.12 Metriken & Attribution

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `normalized_metrics_repository.py` | Persistenz normalisierter Metriken | – | aktiv genutzt |
| `performance_attribution_repository.py` | Persistenz der Performance-Attribution | – | aktiv genutzt |
| `metrics_normalizer.py` | Normalisiert Roh-Metriken | – | **scheint isoliert** |
| `metrics_sync_manager.py` | Synchronisiert Metriken von Plattformen | `metrics_normalizer`, `normalized_metrics_repository`, `platform_raw_metrics_repository` | **scheint isoliert** |
| `platform_raw_metrics_repository.py` | Persistenz von Roh-Plattform-Metriken | – | **scheint isoliert** |
| `publish_result_metrics_bridge.py` | Brücke Publish-Ergebnis → Metriken | `metrics_sync_manager` | **scheint isoliert** |
| `metrics_attribution_bridge.py` | Verknüpft Metriken mit Attribution | `normalized_metrics_repository`, `performance_attribution_builder` | **scheint isoliert** |
| `performance_attribution_builder.py` | Baut Performance-Attribution | – | **scheint isoliert** |

> **Hinweis:** `normalized_metrics_repository` und `performance_attribution_repository` werden von `kpi_dashboard_service` (aktiv) genutzt, aber die Schreib-Seite (sync, bridge, builder) ist nur in Tests vorhanden. Die KPIs zeigen also nur was manuell/historisch eingetragen wurde.

### 1.13 Dashboard-Services

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `kpi_dashboard_service.py` | KPI-Metriken-Aggregation | `comparison_view_builder`, `insight_surface_builder`, `kpi_view_builder`, `normalized_metrics_repository`, `performance_attribution_repository` | aktiv genutzt |
| `kpi_view_builder.py` | KPI-Visualisierung | – | aktiv genutzt |
| `comparison_view_builder.py` | Vergleichs-Metriken-View | – | aktiv genutzt |
| `insight_surface_builder.py` | Generiert Insights | – | aktiv genutzt |
| `feedback_repository.py` | Feedback-Persistenz | – | aktiv genutzt |
| `feedback_manager.py` | Feedback-Verarbeitung | – | aktiv genutzt |
| `feedback_aggregation_service.py` | Aggregiert Feedback-Muster | `feedback_repository` | aktiv genutzt |
| `feedback_context_bridge.py` | Verknüpft Feedback mit Job-Kontext | `feedback_manager` | **scheint isoliert** |
| `feedback_dashboard_service.py` | Feedback-Dashboard-Service | `feedback_aggregation_service`, `feedback_repository` | aktiv genutzt |
| `operations_dashboard_service.py` | Operations-Dashboard-Service | `authorization_service`, `jarvis_status_service` | aktiv genutzt |

### 1.14 Jarvis AI-Assistent

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `jarvis_command_parser.py` | Parst natürlichsprachige Befehle | – | aktiv genutzt |
| `jarvis_command_service.py` | Verarbeitet Jarvis-Befehle | `jarvis_command_parser`, `jarvis_response_builder`, `jarvis_status_service` | aktiv genutzt |
| `jarvis_status_service.py` | Aggregiert System-Status für Jarvis (701 Zeilen) | `feedback_dashboard_service`, `job_loader`, `kpi_dashboard_service`, `maintenance_report_builder`, `publish_guard_repository`, `publish_result_repository`, `queue_store`, `runtime_mode_controller`, `vacation_controller` | aktiv genutzt |
| `jarvis_response_builder.py` | Baut Jarvis-Antworten | – | aktiv genutzt |
| `jarvis_presence_service.py` | Presence-Signale für Jarvis | – | aktiv genutzt |

### 1.15 Monitoring & Recovery

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `integrity_scanner.py` | Validiert System-Integrität (352 Zeilen) | – | aktiv genutzt |
| `recovery_planner.py` | Plant Recovery-Maßnahmen | `integrity_scanner` | aktiv genutzt |
| `retention_planner.py` | Analysiert Retention-Metriken | – | aktiv genutzt |
| `maintenance_report_builder.py` | Baut Wartungs-Reports | `integrity_scanner`, `recovery_planner`, `retention_planner` | aktiv genutzt |
| `maintenance_runner.py` | Führt Wartungsaufgaben aus | `integrity_scanner`, `recovery_executor`, `recovery_planner`, `retention_planner` | **scheint isoliert** |
| `recovery_executor.py` | Führt Recovery-Aktionen aus | `recovery_planner` | **scheint isoliert** |

> **Hinweis:** `maintenance_report_builder` ist aktiv (via `jarvis_status_service`). `maintenance_runner` hingegen ist nur in einem einzigen Test importiert und nie aus einem Entry-Point aufgerufen.

### 1.16 Autorisierung & Workspaces

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `authorization_service.py` | Rollenbasierte Zugriffskontrolle | – | aktiv genutzt |
| `access_context_service.py` | Actor-Kontext-Auflösung | `workspace_repository` | aktiv genutzt |
| `workspace_repository.py` | Multi-Workspace-Konfiguration | – | aktiv genutzt |

### 1.17 Runtime & Mode-Steuerung

| Dateiname | Zweck | Abhängigkeiten (core/) | Status |
|---|---|---|---|
| `runtime_mode_controller.py` | System-weite Mode-Steuerung (pause/resume) | – | aktiv genutzt |
| `vacation_controller.py` | Urlaubs-Modus-Scheduling | – | aktiv genutzt |
| `mode_controller.py` | Mode-Wechsel-Logik | – | aktiv genutzt |

---

## 2. Models-Übersicht (`models/`)

| Dateiname | Was modelliert sie | Primär verwendet in (core/) |
|---|---|---|
| `job.py` | Zentrale Job-Entität (gaming + faceless) | `job_store`, `job_repository`, `job_loader`, `intake_manager`, fast alle Module |
| `timeline_segment.py` | Einzelnes Editing-Segment (hook/build/payoff) | `longform_timeline_builder`, `edit_timeline_repository`, `final_render_driver` |
| `edit_timeline.py` | Vollständige Editing-Timeline | `longform_timeline_builder`, `edit_timeline_repository`, `final_edit_integration` |
| `edit_signal.py` | Frame-Level Signal (Audio/Motion/Silence) | `edit_signal_extractor`, `highlight_selector` |
| `edit_decision.py` | Einzel-Editentscheidung | `final_edit_integration`, `dynamic_edit_plan_repository` |
| `dynamic_edit_plan.py` | Dynamischer Editplan | `dynamic_edit_plan_repository`, `final_edit_integration`, `final_render_driver` |
| `highlight_candidate.py` | Highlight-Kandidat-Segment | `highlight_selector`, `highlight_candidate_repository` |
| `analysis_result.py` | Analyseergebnis (Dauer, Größe, Scores) | `edit_signal_extractor`, `highlight_selector` |
| `reaction_moment.py` | Erkannter Reaktions-Moment | `reaction_moment_detector`, `dynamic_edit_plan_repository` |
| `zoom_instruction.py` | Zoom/Pan-Anweisung für Renderer | `zoom_pacing_engine`, `final_render_driver` |
| `framing_instruction.py` | Framing/Kompositions-Anweisung | `director_engine`, `final_render_driver` |
| `reframe_plan.py` | Vertikaler Reframe-Plan (Shorts) | `reframing_core`, `reframe_plan_repository` |
| `audio_cue.py` | Audio-Cue-Marker | `music_cue_engine`, `music_cue_plan_repository` |
| `audio_mix_instruction.py` | Audio-Mixing-Anweisung | `audio_mix_planner` |
| `music_cue_plan.py` | Musik-Cue-Timing-Plan | `music_cue_engine`, `music_cue_plan_repository` |
| `music_application_plan.py` | Plan für Musik-Anwendung | `music_application_builder`, `music_application_plan_repository` |
| `music_application_instruction.py` | Einzelne Musik-Anwendungsanweisung | `music_application_builder` |
| `music_apply_segment.py` | Musik-Anwendungs-Segment | `music_apply_processor`, `music_apply_timeline_resolver` |
| `music_apply_timeline.py` | Musik-Anwendungs-Timeline | `music_apply_timeline_resolver`, `music_apply_timeline_repository` |
| `local_music_asset.py` | Referenz auf lokale Audio-Datei | `local_music_catalog_repository`, `local_music_selector` |
| `local_music_selection.py` | Ausgewählte lokale Musik | `local_music_selector`, `local_music_selection_repository` |
| `content_variant.py` | Video-Variante (16:9, 9:16, etc.) | `content_variant_builder`, `content_variant_repository` |
| `publish_package.py` | Upload-Payload für Plattform | `publish_package_builder`, `publisher` |
| `publish_decision.py` | Publish-Entscheidung (approved/rejected) | `autopublish_gate`, `publish_guard` |
| `publish_guard_result.py` | Guard-Check-Ergebnis | `publish_guard`, `publish_guard_repository` |
| `publish_result.py` | Upload-Ergebnis mit Metadaten | `publisher`, `publish_result_repository` |
| `metadata_package.py` | Video-Metadaten | `metadata_generator` |
| `title_package.py` | Auto-generierter Titel | `title_generator` |
| `thumbnail_package.py` | Thumbnail-Daten | `thumbnail_forge`, `ai_thumbnail_forge` |
| `subtitle_asset.py` | Generierte Untertitel | `subtitle_processor` |
| `asset.py` | Generisches Asset | `faceless_asset_builder`, `faceless_assembler` |
| `faceless_brief.py` | Faceless-Content-Brief | `faceless_brief_builder`, `faceless_pipeline` |
| `faceless_asset_pack.py` | Faceless-Asset-Bundle | `faceless_asset_builder`, `faceless_assembler` |
| `queue_entry.py` | Publishing-Queue-Eintrag | `queue_store`, `queue_orchestrator` |
| `actor_context.py` | Actor (User) Kontext | `access_context_service`, `authorization_service` |
| `workspace.py` | Workspace-Entität | `workspace_repository` |
| `workspace_membership.py` | Workspace-Rollenzuweisung | `workspace_repository` |
| `trend_signal.py` | Trend-Signal-Daten | `trend_store`, `trend_normalizer` |
| `trend_source.py` | Trend-Quelle (Google Trends, YT, etc.) | `trend_source_connector`, Connectors |
| `trend_qualification.py` | Qualifizierter Trend | `trend_qualifier`, `trend_qualification_store` |
| `opportunity.py` | Opportunity (Trend-basierter Job) | `opportunity_manager`, `opportunity_store` |
| `opportunity_review_view.py` | Opportunity-Review-Anzeige | `opportunity_review_builder` |
| `feedback_record.py` | Feedback-Eintrag | `feedback_repository`, `feedback_manager` |
| `feedback_pattern_summary.py` | Aggregiertes Feedback-Muster | `feedback_aggregation_service` |
| `kpi_view_entry.py` | KPI-Metrik-Eintrag | `kpi_view_builder`, `kpi_dashboard_service` |
| `insight_summary.py` | Generierter Insight | `insight_surface_builder` |
| `comparison_view_summary.py` | Vergleichs-Metriken-Summary | `comparison_view_builder` |
| `normalized_metrics_snapshot.py` | Normalisierter Metriken-Snapshot | `normalized_metrics_repository`, `metrics_normalizer` |
| `platform_raw_metrics.py` | Roh-Plattform-Metriken | `platform_raw_metrics_repository` |
| `performance_attribution_snapshot.py` | Performance-Attribution-Snapshot | `performance_attribution_repository`, `performance_attribution_builder` |
| `scheduling_policy.py` | Publishing-Schedule-Richtlinie | `scheduling_policy_store`, `scheduling_policy_manager` |
| `jarvis_command.py` | Jarvis-KI-Befehl | `jarvis_command_parser`, `jarvis_command_service` |
| `jarvis_presence.py` | Presence-Signal | `jarvis_presence_service` |
| `jarvis_response.py` | KI-Antwort | `jarvis_response_builder`, `jarvis_command_service` |
| `validator_result.py` | Validierungsergebnis | `validator`, `autopublish_gate` |

---

## 3. Entry-Points (Root-Level Python-Dateien)

| Dateiname | Was macht sie | Noch verwendet? |
|---|---|---|
| `app.py` | Haupt-Pipeline-Orchestrator — nimmt einen Job und durchläuft alle Stufen (Analyse, Editing, Rendering, Export, Publish-Vorbereitung). ~2400 Zeilen, 64 Core-Imports. | Ja — zentraler Kern |
| `dashboard.py` | Flask-Web-Dashboard — Monitoring, KPI-Ansicht, Jarvis-Commanddeck, Job-Review, Runtime/Urlaubs-Steuerung. ~2800 Zeilen. | Ja — Web-UI |
| `pipeline_runner.py` | Batch-Dispatcher — scannt `inbox/`, erstellt Jobs, ruft `app.py` auf. Einstiegspunkt für Automatisierung. | Ja — Haupt-Scheduler |
| `processor.py` | Älterer Audio-Energy-Highlighter — extrahiert Highlights per RMS-Energie. Importiert **keine** Core-Module; operiert direkt auf Dateien. | Unklar — möglicherweise Pre-Refactoring-Artefakt; `app.py` nutzt stattdessen `edit_signal_extractor` |
| `assembler.py` | Älterer Video-Concatenator — fügt Clips mit Crossfade zusammen. Importiert ebenfalls **keine** Core-Module. | Unklar — gleiche Funktionalität ist in `final_render_driver` abgebildet |
| `publisher_worker.py` | Publish-Orchestrator — holt fertige Varianten und dispatcht an YouTube/TikTok/Instagram. | Ja — Publishing-Worker |
| `rerender_worker.py` | Rerender-Queue-Prozessor — verarbeitet `rerender_queue.json`. | Ja — aber leerer Smoke-Test (1 Zeile) |
| `patch_render_driver.py` | **Patch-Skript** — deaktiviert den zoompan-Filter in `final_render_driver.py` durch direktes String-Replace. | Temporär — muss manuell ausgeführt werden, kein regulärer Workflow |
| `patch_render_driver_v2.py` | **Patch-Skript v2** — experimentell, fügt 32:9→16:9-Konvertierung + Facecam-PIP hinzu. Unfertig. | Nein — Work-in-Progress, nicht einsatzbereit |
| `reset_jobs.py` | **Utility** — setzt `publish_status` aller Jobs in `exports/` auf `pending`. | Manuelles Ops-Tool |
| `reset_all_jobs.py` | **Utility** — wie `reset_jobs.py`, aber für alle Export-Jobs. | Manuelles Ops-Tool |

---

## 4. Test-Dateien Analyse

### Anzahl
**163 `test_*_smoke.py`-Dateien** — alle direkt im Root-Verzeichnis (kein `tests/`-Ordner).

### Test-Struktur
Die Tests sind **keine pytest-Tests** — sie sind eigenständige Python-Skripte mit `def main()` und `if __name__ == '__main__'`. Sie haben keine automatische Test-Discovery.  
Um einen Test auszuführen: `python test_xyz_smoke.py`.

### Stichprobe (5 Tests)

| Datei | Echte Assertions? | Bewertung |
|---|---|---|
| `test_rerender_worker_smoke.py` | Nein — Datei hat **1 leere Zeile** | Stub ohne jeglichen Wert |
| `test_edit_signal_extractor_smoke.py` | Ja — `assert len(signals) >= 3`, Typ-Checks auf `signal_type` | Echter Integrationstest: erstellt synthetisches Video per FFmpeg, prüft Output |
| `test_highlight_selector_smoke.py` | Ja — gleicher Stil wie oben | Echter Integrationstest |
| `test_final_render_driver_smoke.py` | Ja — erstellt 30s synthetisches Video, prüft Render-Ergebnis | Echter, hochwertiger Integrationstest; testete GPU-Encoding-Pfad |
| `test_access_context_service_smoke.py` | Ja — testet Rollen-Auflösung mit 3 Actor-Typen | Echter Unit-/Integrationstest |

### Gesamtbewertung
**Qualität: Mittelmäßig bis gut — aber strukturell problematisch.**

- **Positiv:** Die meisten Tests haben echte `assert`-Statements und testen konkrete Verhaltensweisen. Tests für `edit_signal_extractor`, `final_render_driver`, `jarvis_*`, `publisher_worker_*` sind substanziell.
- **Negativ 1 — Kein Test-Runner:** Tests können nicht mit `pytest` oder `python -m unittest discover` ausgeführt werden. Es gibt keine CI-Konfiguration.
- **Negativ 2 — `_real_smoke`-Tests sind datenabhängig:** Tests mit `_real_` im Namen greifen auf `data/` und `exports/` zu — sie versagen bei frischer Checkout oder leerem Datenzustand.
- **Negativ 3 — Isolierte Module haben Tests, aber der Code selbst ist isoliert:** Z. B. `test_queue_collision_resolver_smoke.py` existiert, aber `queue_collision_resolver` wird nie aus einem Entry-Point aufgerufen.
- **Negativ 4 — Mindestens 1 echter Stub:** `test_rerender_worker_smoke.py` ist vollständig leer.

---

## 5. Verdächtige Dateien

| Datei | Kategorie | Was ist verdächtig |
|---|---|---|
| `patch_render_driver.py` | **Patch-Skript** | Modifiziert `core/final_render_driver.py` direkt per String-Replace. Deutet auf eine ungeplante Hotfix-Strategie hin. Der Patch selbst (zoompan deaktivieren) sollte im Quellcode stehen, nicht als separates Skript. |
| `patch_render_driver_v2.py` | **Experimentelles Patch-Skript** | Sehr große Datei, beschreibt eine 32:9→16:9-Konvertierung mit Facecam-PIP. Unfertig, nie integriert. Riskant im Repo, weil Inhalt und `final_render_driver.py` leicht auseinanderdriften. |
| `reset_jobs.py` | **Ops-Utility** | Schreibt direkt in `exports/*/job.json`. Kein Logging, keine Bestätigung. Kann unbeabsichtigt alle Jobs auf `pending` zurücksetzen. |
| `reset_all_jobs.py` | **Ops-Utility (Duplikat?)** | Sehr ähnlich zu `reset_jobs.py` — Unterschied unklar ohne tiefere Analyse. Zwei fast-gleiche Utilities im Root. |
| `processor.py` | **Mögliches Legacy-Artefakt** | Importiert keine Core-Module, operiert direkt auf Dateien. Gleiche Aufgabe wie `edit_signal_extractor.py` + `highlight_candidate_repository.py`. Könnte Pre-Refactoring-Code sein, der nie entfernt wurde. |
| `assembler.py` | **Mögliches Legacy-Artefakt** | Gleiche Situation: keine Core-Imports, direkte Dateioperationen. Funktionalität ist in `final_render_driver.py` abgebildet. |
| `director_engine.py` | **Isoliertes Modul** | Beschreibt sich als "pipeline stage 4", hat `if __name__ == '__main__'`-Block, wird aber von keinem anderen Modul je importiert. Ist nie in den aktiven Pipeline-Fluss integriert worden. |

---

## 6. Daten-Übersicht (`data/`)

| Datei | Inhalt |
|---|---|
| `jobs.json` | Master-Job-Registry — alle Jobs mit vollständigem State (Status, Retry-Infos, Scores, Performance-Metriken). Zentrales Daten-Dokument. |
| `rerender_queue.json` | Rerender-Queue — aktuell leer (2 Bytes). |
| `rerender_jobs.json` | Rerender-Job-Metadaten (6,8 KB). |
| `runtime_mode.json` | Aktueller Runtime-Modus (`full_power`, `paused`, etc.). |
| `vacation_state.json` | Urlaubs-Modus-State (enabled/disabled, start\_at, end\_at). |
| `jarvis_config.json` | Jarvis-KI-Konfiguration: Voice-Aktivierung, ElevenLabs Voice-ID, Alert-Intervall. |
| `trend_signals.json` | Trend-Signal-Daten aus Google Trends & YouTube (71 KB — größte Datei). |
| `trend_sources.json` | Konfiguration der Trend-Quellen (2,3 KB). |
| `trend_qualifications.json` | Qualifizierte Trends (1 KB). |
| `opportunities.json` | Identifizierte Opportunities (trend-basierte Jobs) (1 KB). |
| `opportunity_reviews.json` | Opportunity-Review-Records (1,2 KB). |
| `queue_entries.json` | Publishing-Queue-State (1 KB). |
| `scheduling_policies.json` | Publishing-Schedule-Richtlinien pro Channel (1,4 KB). |
| `workspaces.json` | Multi-Workspace-Konfiguration (583 Bytes). |
| `music_catalogs/` | Verzeichnis mit lokalen Musik-Asset-Katalogen (pro Channel). |

---

## Zusammenfassung

**Aktive Kern-Pipeline:**  
`pipeline_runner.py` → `app.py` → 60+ Core-Module → `publisher_worker.py`  
Der Kern ist klar und gut strukturiert.

**Totes Gewicht (nie in Entry-Points aufgerufen):**
- Vollständiges Trends/Opportunities-Subsystem (~14 Module)
- Vollständige Queue-Priorisierungs- und Kollisions-Schicht (~8 Module)
- Vollständige Scheduling-Richtlinien-Schicht (~5 Module)
- Metriken-Sync-Schicht (Schreib-Seite: ~5 Module)
- `director_engine.py` (Stand-alone, nie integriert)
- `feedback_context_bridge.py`, `maintenance_runner.py`, `recovery_executor.py`

Das entspricht ca. **35–40 Core-Module** (ca. 32–36% aller Module), die gebaut, getestet, aber nie in den aktiven Workflow eingebunden wurden.

**Technische Schulden:**
- `processor.py` und `assembler.py` sind wahrscheinlich Pre-Refactoring-Artefakte
- Patch-Dateien (`patch_render_driver*.py`) statt sauberem Code-Fix
- 163 Tests ohne Runner — keine CI-Fähigkeit
- FFmpeg-Pfad `D:\Tools\ffmpeg\bin\ffmpeg.exe` hardcoded in vielen Test-Dateien
