# Zenith Phase 2.B-PRO Analysis

## 1. EXECUTIVE SUMMARY

Zenith ist heute keine reine Review-Only-Pipeline.
Die Phase-2B-Module fuer Review, Story, Render-Planung und Learning sind groesstenteils real in `core/gaming_pipeline.py` verdrahtet, aber sie bleiben ueberwiegend planend/dry-run.
Nach diesen 2B-Gates laeuft trotzdem ein aelterer echter Analyse-, Cut- und FFmpeg-Renderpfad weiter.
Der gemeldete `export_dir`-Crash war echt und hat genau an der Grenze zum Review-Timeline-Block gestoppt.
Nach dem Fix rendert ein synthetischer E2E-Lauf tatsaechlich ein MP4 und wird von `pipeline_runner.py` als ok gemeldet.
Gleichzeitig meldet der Validator im selben Lauf `failed` wegen `Missing thumbnail`; dieser Fehler verhindert den ok-Job nicht.
Die Tests sind breit, aber ueberwiegend Modul-, Contract- und statische Pipeline-Order-Tests.
Vor diesem Audit gab es keinen echten Entry-Point-E2E-Test fuer `pipeline_runner.py`.
Die Nummerierung in Plan/Berichten ist inkonsistent; die angegebenen Ranges ergeben 66 Labels, nicht 64.
Der naechste sinnvolle Schritt ist: Phase 2.B-PRO nicht nach Phase 3 verlassen, sondern erst den echten Renderpfad, die 2B-Gates und die Validator-/Jobstatus-Semantik zu einem einzigen kontrollierten End-to-End-Pfad konsolidieren.

## 2. CRASH-FIX

Bug:

- Realer Lauf crashte mit `UnboundLocalError: cannot access local variable 'export_dir' where it is not associated with a value`.
- Stacktrace aus `exports/gaming_main/job_abd3eac796aa/job.json`:
  - erster Fehler: `core/gaming_pipeline.py`, Zeile 4653, `export_dir=export_dir`
  - Folgefehler im Exception-Handler: `core/gaming_pipeline.py`, Zeile 8801, wieder `export_dir=export_dir`
- Ursache: `run_gaming_pipeline_for_job()` setzte frueh `job_state_export_dir`, nutzte im 2B-32 Review-Timeline-Block aber `export_dir`, bevor eine lokale Zuweisung erreicht wurde. Wegen spaeterer Zuweisungen im selben Funktionsscope war `export_dir` lokal, aber auf diesem Pfad uninitialisiert.

Fix:

- Minimal in `core/gaming_pipeline.py`: direkt nach `job_state_export_dir = ...` wird `export_dir = job_state_export_dir` gesetzt.
- Keine Refactorings, keine weitere Logik geaendert.

Neuer Test:

- `tests/test_pipeline_runner_end_to_end_smoke.py`
- Erzeugt per FFmpeg `lavfi/testsrc + sine` ein 5-Sekunden-Mini-MP4 in `tmp_path`.
- Startet `pipeline_runner.py` als echten Subprozess in isoliertem Workspace mit kopierten Profilen.
- Prueft, dass ein CLI-Job dispatcht wird, `GAMING MAIN` erreicht wird, `Done` erscheint und weder `UnboundLocalError` noch der konkrete `export_dir`-Fehlertext vorkommt.
- Testlauf einzeln: `1 passed, 1 warning in 18.92s`. Die Warnung ist `PytestUnknownMarkWarning` fuer `@pytest.mark.smoke`, weil `pytest.ini` keine Marker registriert und nicht angefasst wurde.

Repro nach Fix:

- No-Arg-Lauf `python pipeline_runner.py > _audit_post_fix_repro.log 2>&1` verarbeitet nichts, weil die reale Inbox-Datei bereits als Job existiert:
  - `INBOX SKIP Rocket League Neuer Test59.mp4 (job already exists)`
  - `Keine aktuellen Rohdateien.`
- Isolierter synthetischer CLI-Lauf `_audit_synthetic_post_fix_cli.log`:
  - `CLI JOB job_71c65e03418a created`
  - `GAMING MAIN ...`
  - echter Render: `RENDER -> output\job_71c65e03418a_final.mp4`
  - Validator: `status=failed reason=Missing thumbnail`
  - trotzdem: `[pipeline_runner] Done - ok=1 skipped=0 failed=0`
  - Exitcode `0`

Commits auf dem Analyse-Branch:

- `716020e chore: ignore runtime preprocessing output`
- `0652e30 fix(pipeline): initialize export_dir in gaming pipeline`

## 3. REPO-INVENTUR

Stand:

- Branch: `analysis/phase-2b-pro-audit-2026-05-15`
- Basis: `fe66631 test(block9): close learning feedback audit`
- Python-Dateien: `1090`
- Python-Zeilen: `214450`
- Testdateien: `446`
- Audit-Smoke-Dateien: `105`
- Block-Audit-Dateien: `41`

Top-Level-Groessen:

| Pfad | Groesse |
|---|---:|
| `core/` | 8,967,290 bytes |
| `models/` | 2,977,121 bytes |
| `tests/` | 627,900,279 bytes |
| `shared/` | 48,365 bytes |
| `storage/` | 11,077 bytes |
| `inbox/` | 2,744,836,705 bytes |
| `exports/` | 174,973,489 bytes |
| `profiles/` | 6,222 bytes |
| `data/` | 160,119,827 bytes |
| `logs/` | 103,565 bytes |

Profile:

- `default.json`
- `gaming_main.json`
- `gaming_uncut.json`
- `reaction_uncut.json`
- `vlog_main.json`
- `vlog_uncut.json`

`profiles/gaming_main.json` ist ein echtes Pro-Profil mit `quality_mode=pro`, `cut_aggressiveness=0.85`, `requires_human_approval=true`, 32:9 -> 16:9 Reframing, Zoom- und Facecam-Optionen.

Stubs/TODOs:

- Nur 3 Treffer fuer `NotImplementedError|TODO|FIXME|XXX` in `core/`, `models/`, `shared/`.
- Alle drei sind erwartete Stub-Pipelines:
  - `core/faceless_pipeline.py`
  - `core/uncut_pipeline.py`
  - `core/vlog_pipeline.py`

## 4. TEST-SUITE-WAHRHEIT

Tatsaechlicher Pytest-Stand nach Fix:

- Befehl: `python -m pytest --cache-clear --tb=short --quiet`
- Ergebnis: `3466 passed, 1 skipped, 1 warning in 19.34s`
- Die historische Zahl `3465 passed / 1 skipped` stimmt fuer `fe66631`; der neue Smoke-Test erhoeht auf 3466.

Skip:

- `tests/test_transcript_real_word_level_probe_smoke.py`
- Grund: `Set ZENITH_REAL_WHISPER_AUDIO_PATH to run a real local Whisper probe.`

Marker:

- `pytest --markers` kennt keinen projektspezifischen `smoke`-Marker.
- Der neue Test nutzt trotzdem `pytest.mark.smoke`; daraus entsteht 1 Warnung.
- Ich habe `pytest.ini` nicht geaendert, weil das ausserhalb der freigegebenen Codeaenderungen lag.

Coverage:

- `coverage` war nicht installiert; Installation via `python -m pip install coverage` war erfolgreich, PowerShell meldete aber einen Warnungs-Exit wegen Script-Pfad nicht auf PATH.
- Coverage-Gesamt: `87%`.
- Niedrige zentrale Module:
  - `core/gaming_pipeline.py`: 12%
  - `core/final_render_driver.py`: 13%
  - `core/edit_signal_extractor.py`: 13%
  - `core/facecam_gameplay_separator.py`: 9%
  - `core/audio_peak_detector.py`: 11%

Test-Stichprobe:

| Datei | Typ | Befund |
|---|---|---|
| `test_block8_pre_execution_safety_contract_audit_smoke.py` | Unit/static contract | In-memory Dict-Fixtures; prueft dry-run Flags. |
| `test_block8_render_export_registry_audit_smoke.py` | Unit/static contract | Liest Registry-Quelltext, synthetische Reports. |
| `test_clip_duration_signal_adapter_smoke.py` | Unit | Adapter-Mapping mit synthetischen Daten. |
| `test_decision_logger_smoke.py` | Kleine Integration | Schreibt Logs/JSONL in `tmp_path`. |
| `test_profanity_censor_runner_smoke.py` | Unit | Synthetische Job-/Transcript-Daten. |
| `test_profile_manager_pipeline_integration_smoke.py` | Kleine Integration | Profile laden, Snapshot schreiben; keine Pipeline. |
| `test_render_verification_contract_registry_integration_smoke.py` | Unit/kleine Integration | Runner + Adapter + Registry mit synthetischen Reports. |
| `test_rms_energy_context_adapter_smoke.py` | Unit/kleine Integration | Synthetische RMS-Punkte plus Silence-Kontext. |
| `test_screen_content_runner_smoke.py` | Integration mit Medien-Stub | Meist monkeypatched, ein OpenCV-Mini-Video, keine Pipeline. |
| `test_timeline_approval_gate_runner_smoke.py` | Unit | Gate-Runner mit synthetischem Job/Plan. |

End-to-End-Suche:

- Vor diesem Audit gab es keine echte `pipeline_runner.py`-Ausfuehrung in Tests.
- Treffer zu `pipeline_runner` waren statische Order-Audits oder Log-Kontext.
- Neuer E2E-Smoke ist der erste echte Entry-Point-Prozesslauf.

Klassen von Bugs, die die alte Suite nicht gefangen hat:

- Lokale Scope-/Pfadfehler in langen Integrationspfaden (`export_dir`).
- Widerspruch zwischen 2B-Review-Gates und spaeterem Legacy-Render.
- Validator meldet `failed`, aber `pipeline_runner.py` macht daraus trotzdem `ok`.
- Reale Whisper-/Transkript-Qualitaet, da der Real-Probe optional geskippt ist.
- Reale grosse Videos, lange Pfade, existierende Jobs und Re-Run-Semantik.

## 5. PIPELINE-INTEGRATION

Entry-Point:

- `pipeline_runner.py` ist der einzige CLI-Entry-Point.
- Inbox-Scan erzeugt Jobs fuer:
  - `gaming_main`
  - `gaming_uncut`
  - `vlog_main`
  - `faceless`
- Nur `gaming_main` hat eine aktive Pipeline.
- Andere Pipelines sind Stubs mit `NotImplementedError`; `pipeline_runner.py` behandelt das als Skip.

Tatsaechlicher Ablauf fuer `gaming_main`:

1. `pipeline_runner.py` scannt Inbox oder CLI-Input.
2. `IntakeManager` erzeugt Job.
3. `_dispatch_pipeline()` ruft `run_gaming_pipeline_for_job()`.
4. `core/gaming_pipeline.py` laedt Profil, schreibt Profile-Snapshot, File-Handler, Preprocessing, Audio/Video/Speech/Content-Analysen.
5. Block 5 bis Block 9 laufen als Review-/Plan-/Dry-Run-Module.
6. Danach laeuft ein aelterer Legacy-Pfad weiter: `TranscriptProcessor`, `GamingAnalyzer`, `GamingCutter`, `EditSignalExtractor`, `LongformTimelineBuilder`, `FinalRenderDriver` oder `RenderProcessor`.
7. Dieser Legacy-Pfad kann echte FFmpeg-Ausgaben schreiben.
8. `pipeline_runner.py` kopiert `output/<job>_final.mp4` nach `exports/<channel>/<job>/<job>_vN_final.mp4`.

Zentrale Tabelle:

| Sub-Phase | Modul-Datei | live in `gaming_pipeline.py`? | Status |
|---|---|---|---|
| 2B-01 | `core/profile_manager.py` | ja | VOLL |
| 2B-02 | `core/file_handler.py` | ja | VOLL, aber ohne 2B-Marker |
| 2B-03 | `core/job_store.py`, `core/job_state_persistence.py` | ja | VOLL, aber ohne 2B-Marker |
| 2B-04 | `core/decision_logger.py`, `core/error_logger.py`, `core/job_recovery.py` | ja | VOLL, aber ohne 2B-Marker |
| 2B-05 | `core/preprocessing_pipeline.py` | ja | VOLL |
| 2B-06 | `core/audio_extraction_planner.py`, `core/audio_extraction_executor.py` | indirekt via 2B-05 | VOLL, aber ohne 2B-Marker |
| 2B-07 | `core/silence_detection_runner.py`, `core/silence_classifier_runner.py` | ja | VOLL |
| 2B-08 | `core/rms_energy_runner.py` | ja | VOLL |
| 2B-09 | `core/energy_peak_runner.py` | ja | VOLL |
| 2B-10 | `core/filler_word_runner.py` | ja | VOLL |
| 2B-11 | `core/audio_normalization_runner.py` | ja | VOLL, Analyse statt Medienaenderung |
| 2B-12 | `core/beat_detection_runner.py` | ja | VOLL |
| 2B-13 | `core/scene_change_runner.py` | ja | VOLL |
| 2B-14 | `core/motion_analysis_runner.py` | ja | VOLL |
| 2B-15 | `core/face_reaction_runner.py` | ja | VOLL |
| 2B-16 | `core/stutter_detection_runner.py` | ja | VOLL |
| 2B-17 | `core/screen_content_runner.py` | ja | VOLL |
| 2B-18 | `core/visual_energy_runner.py` | ja | VOLL |
| 2B-19 | `core/transcript_runner.py` | ja | VOLL, Real-Whisper unbewiesen |
| 2B-20 | `core/sentence_boundary_runner.py` | ja | VOLL als Guard/Report |
| 2B-21 | `core/keyword_emotion_runner.py` | ja | VOLL |
| 2B-22 | `core/interaction_classification_runner.py` | ja | VOLL |
| 2B-23 | `core/dead_content_runner.py` | ja | VOLL |
| 2B-24 | `core/content_value_runner.py` | ja | VOLL |
| 2B-24.5 | `core/profanity_censor_runner.py` | ja | REVIEW-ONLY |
| 2B-25 | `core/segment_classification_runner.py` | ja | REVIEW-ONLY |
| 2B-26 | `core/murch_scoring_runner.py` | ja | REVIEW-ONLY |
| 2B-27 | `core/cut_list_runner.py` | ja | REVIEW-ONLY |
| 2B-28 | `core/clip_duration_runner.py` | ja | REVIEW-ONLY |
| 2B-29 | `core/transition_decision_runner.py` | ja | REVIEW-ONLY |
| 2B-30 | `core/continuity_check_runner.py` | ja | REVIEW-ONLY |
| 2B-31 | `core/cut_list_finalizer_runner.py` | ja | REVIEW-ONLY |
| 2B-32 | `core/review_timeline_plan_runner.py` | ja | REVIEW-ONLY |
| 2B-33 | `core/timeline_approval_gate_runner.py` | ja | REVIEW-ONLY |
| 2B-34 | `core/timeline_safety_validator_runner.py` | ja | REVIEW-ONLY |
| 2B-35 | `core/review_timeline_dashboard_package_runner.py` | ja | REVIEW-ONLY |
| 2B-36 | `tests/test_block6_review_timeline_final_audit_smoke.py` | nein | ISOLIERT/audit-only |
| 2B-37 | `core/hook_identification_runner.py` | ja | REVIEW-ONLY |
| 2B-38 | `core/emotional_arc_runner.py` | ja | REVIEW-ONLY |
| 2B-39 | `core/dynamic_pacing_runner.py` | ja | REVIEW-ONLY |
| 2B-40 | `core/pattern_interrupt_runner.py` | ja | REVIEW-ONLY |
| 2B-41 | `core/reaction_shot_placement_runner.py` | ja | REVIEW-ONLY |
| 2B-42 | `core/but_therefore_story_runner.py` | ja | REVIEW-ONLY |
| 2B-43 | `core/final_quality_validator_runner.py` | ja | REVIEW-ONLY |
| 2B-44 | `tests/test_block7_story_pacing_final_audit_smoke.py` | nein | ISOLIERT/audit-only |
| 2B-45 | `core/render_readiness_guard_runner.py` | ja | REVIEW-ONLY/dry-run |
| 2B-46 | `core/render_plan_runner.py` | ja | REVIEW-ONLY/dry-run |
| 2B-47 | `core/render_command_blueprint_runner.py` | ja | REVIEW-ONLY/non-executable |
| 2B-48 | `core/render_asset_manifest_runner.py` | ja | REVIEW-ONLY/path hints only |
| 2B-49 | `core/render_execution_permission_gate_runner.py` | ja | REVIEW-ONLY |
| 2B-50 | `core/controlled_render_executor_runner.py` | ja | REVIEW-ONLY/dry-run |
| 2B-51 | `tests/test_block8_pre_execution_final_audit_smoke.py` | nein | ISOLIERT/audit-only |
| 2B-52 | `core/ffmpeg_capability_resolver_runner.py` | ja, dynamischer Import | REVIEW-ONLY/tool probe |
| 2B-53 | `core/ffmpeg_command_assembly_runner.py` | ja, dynamischer Import | REVIEW-ONLY/non-executable |
| 2B-54 | `core/controlled_ffmpeg_execution_runner.py` | ja, dynamischer Import | REVIEW-ONLY/dry-run oder smoke-only |
| 2B-55 | `core/output_format_handler_runner.py` | ja | REVIEW-ONLY/contract |
| 2B-56 | `core/render_verification_contract_runner.py` | ja | REVIEW-ONLY/contract |
| 2B-57 | `core/render_dashboard_delivery_package_runner.py` | ja | REVIEW-ONLY |
| 2B-58 | `tests/test_block8_render_export_final_audit_smoke.py` | nein | ISOLIERT/audit-only |
| 2B-59 | `core/feedback_intake_runner.py` | ja | REVIEW-ONLY |
| 2B-60 | `core/style_dna_feedback_updater_runner.py` | ja | REVIEW-ONLY |
| 2B-61 | `core/style_dna_review_gate_runner.py` | ja | REVIEW-ONLY |
| 2B-62 | `core/style_dna_apply_plan_runner.py` | ja | REVIEW-ONLY |
| 2B-63 | `core/style_dna_persistence_gate_runner.py` | ja | REVIEW-ONLY |
| 2B-64 | `core/learning_pattern_recognition_runner.py` | ja | REVIEW-ONLY |
| 2B-65 | `tests/test_block9_learning_feedback_final_audit_smoke.py` | nein | ISOLIERT/audit-only |

Dead-module Stichprobe:

- Keine der geprueften Block-8/9-Stichproben war komplett tot.
- `controlled_render_executor`, `render_dashboard_delivery_package`, `style_dna_persistence_gate`, `learning_pattern_recognition`, `render_verification_contract` haengen ueber Runner und/oder Registry an der Pipeline.
- `controlled_ffmpeg_execution` und `ffmpeg_command_assembly` sind in `gaming_pipeline.py` ueber dynamische Import-Aliases verdrahtet; einfache Greps finden sie daher schlechter.
- Wirklich audit-only sind eher die Abschlussnummern `2B-36`, `2B-44`, `2B-51`, `2B-58`, `2B-65`.

## 6. REVIEW-ONLY-KETTE

Die Behauptung stimmt fuer die 2B-Gates selbst:

- Grep nach `can_render`, `can_apply`, `can_execute`, `can_modify_timeline`, `can_publish` zeigt fast durchgaengig False-Initialisierung und False-Zuruecksetzung.
- Einziger `True`-Treffer in Core/Models ist `core/render_command_blueprint_signal_adapter.py`, aber dort wird ein unerlaubtes `can_execute_now=True` als Blocking-Signal gemeldet. Das ist kein Freigabe-Leak.
- Tests setzen teilweise absichtlich `can_render=True` oder aehnliche Flags, um zu pruefen, dass die Safety-Layer sie wieder blocken.

Der Uebergang zu echter Ausfuehrung ist nicht fertig:

- Es gibt Felder wie `render_execution_human_approved`, `render_execution_approved_by`, `render_execution_allow_real_render`, `ffmpeg_execution_allow_real_render`.
- Es gibt aber keinen klaren User-Flow, der diese Felder kontrolliert setzt.
- Selbst bei angeforderter echter Ausfuehrung blockt `controlled_render_executor` mit `real_render_execution_not_implemented_in_2b_50`.
- `controlled_ffmpeg_execution` verlangt Approval- und Tool-Flags, bleibt aber gate-/smoke-orientiert.

Der groesste architektonische Befund:

- Die 2B-Review-Only-Kette stoppt den Gesamtprozess nicht.
- Nach Block 9 laeuft ein alter Renderpfad weiter.
- Dieser Pfad ruft `FinalRenderDriver().render(...)` oder `RenderProcessor.render(...)` auf und nutzt FFmpeg/Subprocess.
- Der synthetische Post-Fix-Lauf hat tatsaechlich ein MP4 gerendert, obwohl Block 8 selbst `no_render` behauptet.
- Damit ist "alle Blocks sind review_only / no_render / no_execution" nur fuer die neuen 2B-Module wahr, nicht fuer die gesamte `gaming_main`-Pipeline.

## 7. BEKANNTE OFFENE SCHWACHSTELLEN

`analysis.wav` / `music_reference.wav`:

- Die Audiodateien werden inzwischen real erzeugt.
- `core/preprocessing_pipeline.py` baut einen Audio-Extraction-Plan und ruft bei `execute_audio_extraction=True` `execute_audio_extraction_plan(...)`.
- Realer Job `job_abd3eac796aa`:
  - `preprocessed/job_abd3eac796aa/audio/analysis.wav` existiert, 48,142,698 bytes.
  - `preprocessed/job_abd3eac796aa/audio/music_reference.wav` existiert, 48,142,698 bytes.
  - `preprocessed/job_abd3eac796aa/audio/speech_16k_mono.wav` existiert, 8,733,432 bytes.
  - `audio_extraction_status` in `job.json`: `ok`.
- Dieser Punkt ist nicht mehr nur behauptet; die Stage produziert reale Daten.

Whisper-Stabilitaet:

- `core/transcript_processor.py` versucht `faster_whisper` und danach `whisper`.
- `core/transcript_runner.py` behandelt fehlende Engine als `whisper_unavailable`.
- Real-Probe ist optional und wird geskippt, solange `ZENITH_REAL_WHISPER_AUDIO_PATH` nicht gesetzt ist.
- Synthetischer E2E-Lauf:
  - `TRANSCRIPT ... skipped reason=faster-whisper failed: faster-whisper returned no valid segments; whisper failed: whisper returned no valid segments`
- Das ist kontrolliert, aber nicht produktionsstabil. Reale Whisper-Qualitaet ist nicht bewiesen.

`signals=0` / Unified Edit Signal Registry:

- Die neue Registry ist live: `run_unified_edit_signal_registry_for_job(...)` wird vor Block 5 aufgerufen.
- Realer failed Job hatte `unified_edit_signal_status=ok` und `unified_edit_signal_count=1295`.
- Der alte `EditSignalExtractor` ist aber nicht ersetzt; er wird im Legacy-Pfad spaeter weiter genutzt.
- Synthetischer E2E-Lauf hatte im alten Pfad `SIGNALS ... signals=10`.
- Befund: `signals=0` ist fuer den untersuchten Zustand nicht reproduziert, aber Zenith hat zwei Signalwelten: neue Unified Registry und alten Legacy Extractor.

Sentence-Boundary-Protection:

- 2B-20 ist live: `run_sentence_boundary_for_job(...)` und `apply_sentence_boundary_run_report_to_job(...)`.
- Im spaeteren Legacy-Timeline-Pfad baut `SentenceTimelineBuilder` Satzdaten und `LongformTimelineBuilder` ruft `SentenceAtomicityGuard().apply(...)`.
- Schutz wirkt nur, wenn Transkript/Sentence-Timeline vorhanden sind und der Legacy-Timeline-Pfad eine Timeline baut.
- Wenn Whisper fehlt oder keine Timeline entsteht, wird die Protection faktisch nicht relevant.
- Der 2B-20-Report allein garantiert nicht, dass der spaetere echte Renderpfad satzsicher rendert.

## 8. NUMMERIERUNGS-KONSOLIDIERUNG

Harte Inkonsistenzen:

- Der Auftrag nennt "64 Sub-Phasen", aber die angegebenen Ranges ergeben 66 Labels, wenn `2B-24.5` und die Audit-Abschlussnummern mitgezaehlt werden.
- `2B-32` ist im Code eindeutig "Review Timeline Plan".
- Hook Identification ist im Code eindeutig `2B-37`.
- Damit ist der alte Masterplan, der `2B-32` als Hook Identification nennt, falsch fuer den aktuellen Code.
- Im Code gibt es keine Marker fuer `2B-02`, `2B-03`, `2B-04`, `2B-06`, `2B-36`, `2B-44`.
- `2B-51`, `2B-58`, `2B-65` existieren nur als Audit-/Berichtsnummern, nicht als Pipeline-Runner.

Kanonische Code-Liste:

- Block 1 Foundation:
  - 2B-01 Profile Architecture
  - 2B-02 File Handler / Input Acceptance
  - 2B-03 Job System / State Persistence
  - 2B-04 Logging / Recovery / Debug
  - 2B-05 Preprocessing Pipeline
- Block 2 Audio Intel:
  - 2B-06 Audio Extraction inside Preprocessing
  - 2B-07 Silence Detection / Adaptive Silence
  - 2B-08 RMS Energy
  - 2B-09 Energy Peak Detection
  - 2B-10 Filler Word Detection
  - 2B-11 Audio Normalization Analysis
  - 2B-12 Beat Detection
- Block 3 Video Intel:
  - 2B-13 Scene Change
  - 2B-14 Motion Analysis
  - 2B-15 Face Reaction
  - 2B-16 Stutter Detection
  - 2B-17 Screen Content
  - 2B-18 Visual Energy
- Block 4 Speech & Content:
  - 2B-19 Speech-to-Text
  - 2B-20 Sentence Boundary
  - 2B-21 Keyword Emotion
  - 2B-22 Interaction Classification
  - 2B-23 Dead Content
  - 2B-24 Content Value
- Block 4.5:
  - 2B-24.5 Profanity Censor SFX
- Block 5 Cutting Decision:
  - 2B-25 Segment Classification
  - 2B-26 Murch Scoring
  - 2B-27 Cut List Generation
  - 2B-28 Clip Duration
  - 2B-29 Transition Decision
  - 2B-30 Continuity Check
  - 2B-31 Cut List Finalization
- Block 6 Review Timeline:
  - 2B-32 Review Timeline Plan
  - 2B-33 Timeline Approval Gate
  - 2B-34 Timeline Safety Validator
  - 2B-35 Review Timeline Dashboard Package
  - 2B-36 Block 6 Final Audit only
- Block 7 Story & Pacing:
  - 2B-37 Hook Identification
  - 2B-38 Emotional Arc
  - 2B-39 Dynamic Pacing
  - 2B-40 Pattern Interrupt
  - 2B-41 Reaction Shot Placement
  - 2B-42 But/Therefore Story
  - 2B-43 Final Quality Validator
  - 2B-44 Block 7 Final Audit only
- Block 8 Render & Export:
  - 2B-45 Render Readiness Guard
  - 2B-46 Render Plan
  - 2B-47 Render Command Blueprint
  - 2B-48 Render Asset Manifest
  - 2B-49 Render Execution Permission Gate
  - 2B-50 Controlled Render Executor
  - 2B-51 Pre-Execution Final Audit only
  - 2B-52 FFmpeg Capability Resolver
  - 2B-53 FFmpeg Command Assembly
  - 2B-54 Controlled FFmpeg Execution
  - 2B-55 Output Format Handler
  - 2B-56 Render Verification Contract
  - 2B-57 Render Dashboard Delivery Package
  - 2B-58 Render/Export Final Audit only
- Block 9 Learning/Feedback:
  - 2B-59 Feedback Intake
  - 2B-60 Style DNA Feedback Updater
  - 2B-61 Style DNA Review Gate
  - 2B-62 Style DNA Apply Plan
  - 2B-63 Style DNA Persistence Gate
  - 2B-64 Learning Pattern Recognition
  - 2B-65 Block 9 Final Audit only

Empfehlung: Master-Chat sollte diese Liste als neue kanonische Wahrheit verwenden und die alte `2B-32 Hook`-Angabe streichen.

## 9. EHRLICHER REIFEGRAD

Kategorisierung der 66 Code-/Berichtslabels:

| Kategorie | Anzahl | Bedeutung |
|---|---:|---|
| VOLL | 24 | In Pipeline integriert und als Analyse-/Foundation-Stage real lauffaehig. |
| REVIEW-ONLY | 37 | In Pipeline integriert, aber planend/dry-run/no media mutation. |
| ISOLIERT | 5 | Audit-only Nummern ohne Runtime-Runner: 2B-36, 2B-44, 2B-51, 2B-58, 2B-65. |
| LUECKE | 0 | Kein vollstaendig fehlendes Modul fuer die kanonische Code-Liste gefunden; mehrere Nummern sind aber unmarkiert/inferiert. |

Ehrlicher Reifegrad fuer "Zenith schneidet wirklich gut Videos":

- Als Modul-/Audit-Ausbau: ca. 80-85%.
- Als echte, konsistente End-to-End-Produktionspipeline: ca. 35%.

Warum nicht hoeher:

- Zenith kann heute Jobs anlegen, Preprocessing ausfuehren, Audio/Video-Analysen erzeugen und ein MP4 rendern.
- Aber der echte Render kommt aus einem Legacy-Pfad, nicht aus dem Block-8-Review-/Approval-/Controlled-Execution-Pfad.
- Der Validator kann `failed` melden, waehrend `pipeline_runner.py` trotzdem `ok=1` ausgibt.
- Reale Whisper-Qualitaet ist nicht verifiziert.
- Die neuen 2B-Cut-/Review-Artefakte werden nicht eindeutig als einzige Wahrheit in den finalen Render eingespeist.
- Es gibt keine klare Approval-Oberflaeche oder Setter-Logik fuer den Uebergang von Review zu echter Ausfuehrung.

Was Zenith heute kann:

- Reale Preprocessing-Audioartefakte erzeugen.
- Viele Analyse- und Review-Reports schreiben.
- Unified edit signals erzeugen.
- Mit einem Mini-Clip end-to-end ein MP4 rendern.

Was fehlt fuer "200-Euro-Cutter-Niveau":

- Ein einziger autoritativer Cut-/Timeline-Plan.
- Ein kontrollierter Renderpfad, der genau diesen Plan ausfuehrt.
- Satz-/Continuity-/Approval-Gates muessen den echten Render blocken oder erlauben, nicht nur Reports erzeugen.
- Validator-Fehler muessen Jobstatus und Pipeline-Ergebnis korrekt beeinflussen.
- Reale Transkription muss stabil laufen.

## 10. EMPFEHLUNGEN FUER DEN MASTER-CHAT

Prioritaet 1:

- Den Legacy-Renderpfad hinter Block 9 stoppen oder offiziell in den kontrollierten 2B-Renderpfad integrieren.
- Eine Entscheidung erzwingen: entweder 2B bleibt komplett review-only und rendert nie, oder Approval + Controlled Execution fuehrt wirklich den finalen 2B-Plan aus.

Prioritaet 2:

- Jobstatus/Validator-Semantik reparieren.
- Ein Lauf mit `VALIDATE status=failed` darf nicht als `ok=1` und assembled durchgehen, ausser es gibt eine bewusst dokumentierte "rendered_but_validation_failed"-Zwischenstufe.

Prioritaet 3:

- Echte E2E-Testmatrix aufbauen:
  - Mini-Video ohne Speech
  - Mini-Video mit Speech/Transcript-Testmode
  - Missing thumbnail/validator-failed
  - Approval missing
  - Approval present, real render allowed
  - Re-run existing job / already exists

Empfehlung zu Phase 3:

- Nicht zu Phase 3 (Shorts) weitergehen, bevor 2.B-PRO sauber integriert ist.
- Phase 3 wuerde sonst auf einer Pipeline aufbauen, die gleichzeitig Review-Only behauptet und real rendert.

Minimaler Eingriff fuer "schneidet ein Video end-to-end":

1. Einen einzigen finalen Timeline-/Cut-Plan als Quelle festlegen: entweder 2B final cut list oder Legacy `LongformTimelineBuilder`.
2. Render nur ueber eine Funktion ausfuehren lassen.
3. Approval-/Safety-/Validator-Status vor und nach Render hart auswerten.
4. `pipeline_runner.py` darf nur `ok` melden, wenn Render und Validation konsistent erfolgreich sind.
5. Den neuen E2E-Smoke zu einer kleinen E2E-Suite ausbauen.

## 11. ANHANG

Erzeugte Audit-Artefakte:

- `_audit_all_2b_markers.txt`
- `_audit_approval_flow_search.txt`
- `_audit_audio_artifacts_search.txt`
- `_audit_coverage.txt`
- `_audit_coverage_install.log`
- `_audit_coverage_pytest.log`
- `_audit_dead_module_samples.txt`
- `_audit_e2e_search.txt`
- `_audit_final_audit_files.txt`
- `_audit_gaming_pipeline_2b_markers.txt`
- `_audit_gaming_pipeline_calls_grep.txt`
- `_audit_gaming_pipeline_imports.txt`
- `_audit_initial_repro.log`
- `_audit_post_fix_repro.log`
- `_audit_pytest_full.log`
- `_audit_pytest_mark_usage.txt`
- `_audit_pytest_markers.txt`
- `_audit_pytest_skips.log`
- `_audit_repo_inventory.txt`
- `_audit_review_only_flags.txt`
- `_audit_review_only_tests.txt`
- `_audit_review_only_true_flags.txt`
- `_audit_sentence_boundary_search.txt`
- `_audit_signal_path_summary.txt`
- `_audit_signal_registry_search.txt`
- `_audit_synthetic_ffmpeg_create.log`
- `_audit_synthetic_post_fix_cli.log`
- `_audit_test_sample_classification.txt`
- `_audit_test_sample_files.txt`
- `_audit_unique_2b_markers.txt`
- `_audit_whisper_search.txt`

Geaenderte Dateien:

- Hygiene-Commit:
  - `.gitignore`
- Fix-Commit:
  - `core/gaming_pipeline.py`
  - `tests/test_pipeline_runner_end_to_end_smoke.py`
- Audit-Commit:
  - `ZENITH_PHASE_2B_PRO_ANALYSIS.md`
  - `_audit_*.log`
  - `_audit_*.txt`

Nicht gepusht:

- Kein Push auf `main`.
- Branch wartet auf Master-Chat-Review.
