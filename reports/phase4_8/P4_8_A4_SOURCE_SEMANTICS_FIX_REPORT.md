# P4.8-A4 Source Semantics Fix Report

## Status

READY_FOR_20_PAIR_RUN = no

Kein 20-Pair-Bulk-Lauf wurde gestartet.
Keine A5/B1/B2-Subphase wurde gestartet.

## Geaenderte Dateien

- `scripts/p4_8_a4_reingest_pairs.py`
- `reports/phase4_8/P4_8_A4_SOURCE_SEMANTICS_FIX_REPORT.md`
- `reports/phase4_8/PROGRESS_P4_8.md`

## Gefundene Ursache

- Hook kam vorher aus dem allgemeinen A4-Transcript und hatte keine saubere Final-Quelle.
- Style-Capture nutzte `source_video(pair_dir)`, das fuer Pairs `raw.mp4` bevorzugt. Dadurch standen `p4_8_a4_style_capture_source` und `p4_6_analysis_source` beide auf Raw.
- Raw/Final wurden fachlich vermischt: Final-Scene-Changes aus `final.mp4`, aber Style-Capture-Dauer aus `raw.mp4`.
- Dadurch entstanden Widersprueche in `cut_density_curve`, `opening_pattern` und `closing_pattern`.
- `speaker_distribution` war zu selbstsicher, weil A4 keine echte Speaker-Zuordnung per Transcript/Voice-Reference verifiziert hat.

## Code-Fundstellen

| Feldbereich | Datei/Funktion |
|---|---|
| `hook`, `first_words` | `scripts/p4_8_a4_reingest_pairs.py`, `base_fingerprint_stage`, `build_final_hook`; `scripts/p4_7_5_rerun_hook.py` |
| `p4_8_a4_style_capture_source`, `style_capture` | `scripts/p4_8_a4_reingest_pairs.py`, `extend_style_capture`; `core/style_capture_analyzer.py` |
| `opening_pattern`, `closing_pattern`, `cut_density_curve`, `scene_duration_stats` | `core/style_capture_analyzer.py`; post-processing in `scripts/p4_8_a4_reingest_pairs.py` |
| `facial_expression_distribution` | `scripts/extend_p4_6_fingerprints.py`; A4 metadata in `scripts/p4_8_a4_reingest_pairs.py` |
| `speaker_distribution` | `scripts/extend_p4_6_fingerprints.py`; A4 confidence downgrade in `scripts/p4_8_a4_reingest_pairs.py` |
| `reaction_timing` | `core/learning_corpus_reaction_timing.py`; A4 reason metadata in `scripts/p4_8_a4_reingest_pairs.py` |
| `transcript.first_10s_text` | `core/learning_corpus_transcript.py`; A4 bounded helper in `scripts/p4_8_a4_reingest_pairs.py` |

## Neue Source-Regeln

Final `final.mp4`:

- `hook`
- `scene_changes`
- `pacing`
- `audio` fuer Viewer-/Final-Audio
- `style_capture.cut_density_curve`
- `style_capture.opening_pattern`
- `style_capture.closing_pattern`
- `style_capture.scene_duration_stats`
- `style_capture.intensity_clustering`

Raw `raw.mp4`:

- `p4_6_analysis_source`
- `voice_intensity_distribution`
- `facial_expression_distribution`
- `gameplay_ratio`
- Raw Facecam/Gameplay-Erkennung

Raw mixed `raw_mixed_audio.mp4`:

- A4 bounded main transcript (`transcript.source = raw_mixed_audio`)
- Multi-track-kompatible Audioanalyse fuer Rohmaterial, wenn explizit markiert

## Neue Schutzmechanismen

- Hook wird via `build_final_hook()` aus `final.mp4` transkribiert.
- Kein stiller Hook-Fallback auf Raw.
- `scene_changes`, `pacing`, `audio` und `style_capture` werden fuer Style-Semantik aus `final.mp4` berechnet.
- `opening_pattern.first_cut_at_seconds` wird auf den ersten globalen Final-Scene-Cut gesetzt.
- `opening_pattern.first_cut_in_hook_window_seconds` beschreibt separat den ersten Cut innerhalb des 30s-Hook-Fensters.
- `closing_pattern.last_cut_at_seconds_before_end` wird als `final_duration_seconds - last_scene_change_timestamp` gesetzt.
- `facial_expression_distribution_multi_label = true` und Hinweistext dokumentieren ueberlappende Raten.
- `speaker_distribution` wird auf `requires_multi_track_transcript` mit `confidence=0.0` heruntergestuft.
- `reaction_timing.applicable=false` erhaelt einen Reason, wenn Reaction-Density nur als Dichte geschaetzt wurde.
- `source_semantics_checks()` prueft Final-Quellen, Cut-Density-Bins, Opening und Closing im finalen Pair-Audit.

## Tests

```powershell
python -m py_compile scripts\p4_8_a4_reingest_pairs.py
```

Ergebnis: PASS, Exitcode 0.

`pytest` wurde nicht ausgefuehrt, weil `pair_002` im vorgeschriebenen Kontrolllauf fehlgeschlagen ist und die STOPP-Regel greift.

## pair_001 Ergebnis

Ergebnis: SUCCESS.

| Punkt | Wert |
|---|---|
| Fingerprint | `learning_corpus/pairs/pair_001/style_fingerprint.json` |
| Pair-Report | `reports/phase4_8/p4_8_a4_pair_reports/pair_001_source_semantics_fix.json` |
| Log | `reports/phase4_8/p4_8_a4_logs/pair_001_source_semantics_fix.log` |
| Completed Marker | ja, `p4_8_a4_pair_completed pair=pair_001` |
| `hook.source` | `final` |
| `hook.source_path` | `learning_corpus\pairs\pair_001\final.mp4` |
| `hook.analysis_window_seconds` | 30 |
| `p4_8_a4_style_capture_source` | `learning_corpus\pairs\pair_001\final.mp4` |
| Cut-Density plausibel | ja, Source-Audit ok |
| Opening plausibel | ja, `first_cut_at_seconds=40.583` |
| Closing plausibel | ja, `last_cut_at_seconds_before_end=0.55` |

Stage-Dauern:

| Stage | Status | Dauer |
|---|---|---:|
| prepare_audio | ok | 0s |
| transcript | ok | 10s |
| base_fingerprint_write | ok | 414s |
| p4_6_extension | ok | 352s |
| p4_7_repairs | ok | 0s |
| style_capture | ok | 0s |
| final_audit | ok | 0s |

## pair_002 Ergebnis

Ergebnis: FAILED.

| Punkt | Wert |
|---|---|
| Fingerprint | `learning_corpus/pairs/pair_002/style_fingerprint.json` bleibt vom vorherigen A4-Fix-Lauf erhalten und ist fuer Source-Semantik nicht freigegeben |
| Pair-Report | `reports/phase4_8/p4_8_a4_pair_reports/pair_002_source_semantics_fix.json` |
| Log | `reports/phase4_8/p4_8_a4_logs/pair_002_source_semantics_fix.log` |
| Completed Marker | nein |
| Failed Stage | `base_fingerprint_write` |
| Exception | `RuntimeError: transcript helper failed returncode=3221226505` |
| Ursache | Final-Hook-Transcript-Helper auf `pair_002/final.mp4` ist als Subprozess nativ abgestuerzt |

Stage-Dauern:

| Stage | Status | Dauer |
|---|---|---:|
| prepare_audio | ok | 0s |
| transcript | ok | 6s |
| base_fingerprint_write | failed | 11s |

Da Hook laut neuer Regel nicht still auf Raw fallen darf, ist dieser Failure korrekt blockierend.

## Korpus-Stand

| Bereich | style_fingerprint.json |
|---|---:|
| `learning_corpus/pairs` | 2 |
| `learning_corpus/top_solo` | 30 |
| `learning_corpus/vlogs` | 3 |

## Entscheidung

READY_FOR_20_PAIR_RUN = no

Naechster Fix vor Bulk: Final-Hook-Transkript fuer `pair_002/final.mp4` muss robust werden, ohne Raw-Fallback. Wahrscheinlich ist ein isolierter Hook-Transkriptionspfad noetig, der FFmpeg-Extraktion, WAV-Validierung und Whisper/Fallback-Policy getrennt reportet.

