# Signal Architecture — Render Source of Truth

Stand: Zenith 2.C.4, `main` bei Ausgangs-HEAD `7bc5117`.

## Autoritative Kurzfassung

Die Render-Wahrheit pro Job ist die `EditTimeline`, konkret `edit_timeline.selected_segments`, sobald eine Longform-Timeline gebaut wurde.

Der echte Render-Pfad lautet:

```text
GamingPipeline
  -> EditSignalExtractor.extract(...)
  -> HighlightSelector.select(...)
       -> highlight_candidates
       -> weak_zones
  -> LongformTimelineBuilder.build(...)
       -> EditTimeline(selected_segments)
  -> FinalRenderDriver.render(..., edit_timeline=EditTimeline, ...)
       -> rendert genau diese selected_segments
```

Die `unified_edit_signal_registry.py` ist derzeit keine Render-Wahrheit. Sie normalisiert und aggregiert viele Analyse-/Review-/Audit-Signale in ein gemeinsames Registry-Format und schreibt diese Zusammenfassung auf den Job. Der Produktions-Render-Pfad liest diese Registry-Ausgabe aktuell nicht für Schnittentscheidungen.

## 1. EditSignalExtractor

### Zweck im Render-Pfad

`EditSignalExtractor` ist die kompakte Render-nahe Signalquelle für den Longform-Schnitt. Seine `EditSignal`-Objekte werden von `HighlightSelector` in `highlight_candidates` und `weak_zones` übersetzt. Diese Kandidaten/Zonen werden danach an `LongformTimelineBuilder.build(...)` übergeben und beeinflussen damit die `EditTimeline`, die der `FinalRenderDriver` rendert.

### EditSignal-Format

`models/edit_signal.py` definiert `EditSignal` als Dataclass mit diesem Format:

```text
signal_id: str
job_id: str
start_time: float
end_time: float
signal_type: str
strength: float
confidence: float
source: str
tags: list[str]
notes: list[str]
metadata: dict[str, object]
created_at: datetime
updated_at: datetime
```

Zusätzlich gibt es die Property:

```text
duration = max(0.0, end_time - start_time)
```

### signal_type-Werte

Der aktuelle Extractor erzeugt diese sieben `signal_type`-Werte:

```text
duration_context
audio_peak
silence_zone
audio_activity
motion_peak
low_motion_zone
motion_activity
```

### Quellen im Extractor

```text
edit_signal_extractor.analysis -> duration_context
edit_signal_extractor.audio    -> audio_peak | silence_zone | audio_activity
edit_signal_extractor.video    -> motion_peak | low_motion_zone | motion_activity
```

### Aufrufstellen und Konsumenten

Produktiver Pipeline-Aufruf:

```text
core/gaming_pipeline.py
  edit_signals = EditSignalExtractor().extract(job, analysis_result)
```

Direkte Konsumenten dieser Ausgabe im Pipeline-Pfad:

```text
EnergyCurveBuilder.build(edit_signals=...)
AudioRoleIndicatorBuilder.build(edit_signals=...)
GameplayEventIndicatorBuilder.build(edit_signals=...)
RoundPhaseDetector.detect(edit_signals=...)
HighlightSelector.select(..., edit_signals)
CutIndicatorBuilder.build(edit_signals=...)
ReactionMomentDetector.detect(edit_signals=...)
```

Wichtige Render-Brücke:

```text
EditSignalExtractor
  -> edit_signals
  -> HighlightSelector
  -> highlight_candidates + weak_zones
  -> LongformTimelineBuilder
  -> EditTimeline
  -> FinalRenderDriver
```

## 2. Unified Edit Signal Registry

### Zweck

`core/unified_edit_signal_registry.py` ist ein Aggregations-/Audit-Modul. Es sammelt Signale aus vielen Analyse-, Review-, Safety-, Render- und Learning-Berichten, normalisiert sie auf ein gemeinsames Dict-Format, dedupliziert sie und speichert das Ergebnis am Job.

Aktuell ist diese Registry nicht die Quelle, die den finalen Schnitt im Produktions-Render bestimmt.

### Normalformat

Jedes normalisierte Registry-Signal hat dieses Dict-Format:

```text
signal_id
signal_type
source
start_seconds
end_seconds
center_seconds
duration_seconds
signal_score
priority
action_hint
reason
confidence
metadata
source_payload
```

### Registry-Resultat am Job

`apply_unified_edit_signal_result_to_job(...)` schreibt:

```text
job.unified_edit_signal_report
job.unified_edit_signal_status
job.unified_edit_signals
job.unified_edit_signal_count
job.unified_edit_signal_summary
job.unified_edit_signal_recommendation
```

### Adapterquellen

Die Registry kennt aktuell diese Quellen:

```text
energy_peak
filler_word
interaction_classification
keyword_emotion
dead_content
content_value
profanity_censor
audio_normalization
beat_detection
scene_change
motion_analysis
face_reaction
stutter_detection
screen_content
sentence_boundary
visual_energy
segment_classifier
murch_scoring
cut_list_generator
clip_duration_optimizer
transition_decision
continuity_check
cut_list_finalizer
review_timeline_plan
timeline_approval_gate
timeline_safety_validator
review_timeline_dashboard_package
hook_identification
emotional_arc
dynamic_pacing
pattern_interrupt
reaction_shot_placement
but_therefore_story
final_quality_validator
render_readiness_guard
render_plan
render_command_blueprint
render_asset_manifest
render_execution_permission_gate
controlled_render_executor
controlled_ffmpeg_execution
output_format_contract
render_verification_contract
render_dashboard_delivery_package
feedback_intake
style_dna_feedback_update
style_dna_review_gate
style_dna_apply_plan
style_dna_persistence_gate
learning_pattern_recognition
ffmpeg_capability_resolver
ffmpeg_command_assembly
silence_classification
silence_detection
```

### Aufrufstellen und Konsumenten

Die Registry-Funktionen sind:

```text
build_unified_edit_signal_result(job, ...)
apply_unified_edit_signal_result_to_job(job, result)
run_unified_edit_signal_registry_for_job(job, ...)
```

Gefundene Nutzung: Registry-Smoke-/Integrationstests und Proof-/Audit-Skripte. Im geprüften Produktions-Render-Pfad (`gaming_pipeline.py` -> `LongformTimelineBuilder` -> `FinalRenderDriver`/`RenderProcessor`) wird die Registry-Ausgabe nicht gelesen.

## 3. Render-Wahrheit im Detail

### Was speist LongformTimelineBuilder.build(...)?

`LongformTimelineBuilder.build(...)` erhält:

```text
job
analysis_result
highlight_candidates
weak_zones
energy_curve_result
gameplay_vision_result
facecam_reaction_result
transcript_result
cut_indicator_result
cut_scoring_profile
sentence_timeline_result
audio_role_result
round_phase_result
gameplay_state_result
universal_moment_result
```

### Herkunft der Inputs

Aus `EditSignalExtractor` direkt oder indirekt:

```text
edit_signals
  -> HighlightSelector -> highlight_candidates
  -> HighlightSelector -> weak_zones
  -> EnergyCurveBuilder -> energy_curve_result
  -> AudioRoleIndicatorBuilder -> audio_role_result
  -> GameplayEventIndicatorBuilder -> gameplay_event_result
  -> RoundPhaseDetector -> round_phase_result
  -> CutIndicatorBuilder -> cut_indicator_result
  -> UniversalMomentBrain -> universal_moment_result
```

Direkt aus Analyse-/Pipeline-Modulen:

```text
analysis_result
transcript_result
sentence_timeline_result
gameplay_vision_result
facecam_reaction_result
facecam_emotion_result
gameplay_state_result
cut_scoring_profile
```

Nicht aus der Unified Registry:

```text
unified_edit_signal_report
unified_edit_signals
unified_edit_signal_summary
unified_edit_signal_recommendation
```

Diese Registry-Felder werden im echten Render-Pfad nicht an `LongformTimelineBuilder`, `FinalRenderDriver` oder den `RenderProcessor` übergeben.

## 4. Render-Datenfluss

```text
[Raw Job + Analysis]
        |
        v
[EditSignalExtractor]
        |  EditSignal list
        v
[HighlightSelector]
        |  highlight_candidates + weak_zones
        v
[LongformTimelineBuilder]
        |  plus direct analysis objects:
        |  energy_curve_result
        |  gameplay_vision_result
        |  facecam_reaction_result
        |  transcript_result
        |  cut_indicator_result
        |  sentence_timeline_result
        |  audio_role_result
        |  round_phase_result
        |  gameplay_state_result
        |  universal_moment_result
        v
[EditTimeline]
        |  selected_segments
        v
[FinalRenderDriver]
        |  renders selected_segments
        v
[Final MP4]
```

Parallel, derzeit nicht render-bestimmend:

```text
[Many module reports]
        |
        v
[Unified Edit Signal Registry]
        |  unified_edit_signal_report / unified_edit_signals on Job
        v
[Audit / Review / possible future cleanup or integration]
```

## 5. Entscheidung für 2.C.4

Fall A ist aktiv: Die Quellen sind ausreichend klar getrennt.

- Render-Wahrheit: `EditTimeline.selected_segments`, gebaut durch `LongformTimelineBuilder`.
- Render-nahe Signalquelle: `EditSignalExtractor` über `HighlightSelector` und direkte Analyseobjekte.
- Unified Registry: derzeit Audit-/Review-Aggregation; nicht im Render-Pfad konsumiert.
- Kein Code-Löschvorgang in 2.C.4.
- Kein Render-Pfad-Umbau in 2.C.4.

## 6. Cleanup-Hinweis

Falls die Unified Registry dauerhaft nicht im Render-Pfad verwendet werden soll, ist sie ein Kandidat für späteren Cleanup oder klare Dashboard-/Audit-Anbindung. Dieser Cleanup ist bewusst nicht Teil von 2.C.4.
