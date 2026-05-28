# P4.8-A4 Final Transcript Fix Report

## Status

READY_FOR_20_PAIR_RUN = yes

Bulk wurde nicht gestartet. A5/B1/B2 wurden nicht gestartet. Kein Commit wurde erstellt.

## Geaenderte Dateien

- `scripts/p4_8_a4_reingest_pairs.py`
- `reports/phase4_8/P4_8_A4_FINAL_TRANSCRIPT_FIX_REPORT.md`
- `reports/phase4_8/PROGRESS_P4_8.md`

## Ursache

Das Hauptfeld `transcript` kam vorher aus `raw_mixed_audio`. Das war fachlich falsch bzw. gefaehrlich, weil `transcript` im Style-Fingerprint den Zuschauer-Final-Transcript beschreiben soll.

## Neue Transcript-Regel

- `transcript` beschreibt jetzt `viewer_final_transcript` aus `final.mp4`.
- `transcript.source = "final"`.
- `transcript.source_path` zeigt auf `learning_corpus\pairs\<pair>\final.mp4`.
- `raw_mixed_audio` steht nicht mehr im Hauptfeld `transcript`.
- Raw/Mixed-Transcript ist nur separat erlaubt, z.B. als `raw_mixed_transcript` mit `scope = "raw_material_analysis"`.

## Neue robuste Pipeline

- Stage `final_transcript_audio_extract`: extrahiert aus `final.mp4` WAV-Kandidaten mit 75s, 45s und 30s.
- WAV-Format: mono, 16 kHz, `pcm_s16le`.
- Stage `final_transcript`: transkribiert nur diese WAVs im isolierten Helper-Subprozess.
- Retry-Reihenfolge: 75s -> 45s -> 30s.
- Kein Raw-Fallback im Hauptfeld `transcript`.
- Wenn alle Versuche scheitern, faellt das Pair mit `failed_stage = final_transcript` durch.
- `first_10s_text` wird im finalen A4-Pair-Fingerprint entfernt, wenn das effektive Transcript-Fenster nicht exakt 10s ist; `first_window_text` bleibt erhalten.

## Ergebnis pair_001

- Fingerprint: `learning_corpus\pairs\pair_001\style_fingerprint.json`
- Pair-Report: `reports\phase4_8\p4_8_a4_pair_reports\pair_001_final_transcript_fix.json`
- Log: `reports\phase4_8\p4_8_a4_logs\pair_001_final_transcript_fix.log`
- Completed Marker: ja
- Reportstatus: `ok`
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: vorhanden
- `transcript.source`: `final`
- `transcript.source_path`: `learning_corpus\pairs\pair_001\final.mp4`
- `transcript.scope`: `viewer_final_transcript`
- `transcript.effective_window_seconds`: 75.0
- `transcript.first_window_text` vorhanden: ja
- `transcript.first_10s_text` vorhanden: nein
- `raw_mixed_audio` im Haupt-Transcript: nein
- `hook.source`: `final`
- `hook.effective_window_seconds`: 30.0
- `p4_8_a4_style_capture_source`: `learning_corpus\pairs\pair_001\final.mp4`
- Source-Audit: ok

## Ergebnis pair_002

- Fingerprint: `learning_corpus\pairs\pair_002\style_fingerprint.json`
- Pair-Report: `reports\phase4_8\p4_8_a4_pair_reports\pair_002_final_transcript_fix.json`
- Log: `reports\phase4_8\p4_8_a4_logs\pair_002_final_transcript_fix.log`
- Completed Marker: ja
- Reportstatus: `ok`
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: vorhanden
- `transcript.source`: `final`
- `transcript.source_path`: `learning_corpus\pairs\pair_002\final.mp4`
- `transcript.scope`: `viewer_final_transcript`
- `transcript.effective_window_seconds`: 75.0
- `transcript.first_window_text` vorhanden: ja
- `transcript.first_10s_text` vorhanden: nein
- `raw_mixed_audio` im Haupt-Transcript: nein
- `hook.source`: `final`
- `hook.effective_window_seconds`: 20.0
- `p4_8_a4_style_capture_source`: `learning_corpus\pairs\pair_002\final.mp4`
- Source-Audit: ok

## Korpus-Stand

- `learning_corpus\pairs`: 2 `style_fingerprint.json`
- `learning_corpus\top_solo`: 30 `style_fingerprint.json`
- `learning_corpus\vlogs`: 3 `style_fingerprint.json`

## Nicht bearbeitet

- `learning_corpus\pairs_singletrack_backup`
- `learning_corpus\top_solo`
- `learning_corpus\vlogs`

## Tests

- `python -m py_compile scripts\p4_8_a4_reingest_pairs.py` -> PASS
- Kein pytest ausgefuehrt.

Hinweis: Die PowerShell/Tee-Ausgabe zeigt MediaPipe/TFLite-Stderr weiterhin als `NativeCommandError`-Text. Die A4-Erfolgskriterien werden ueber PairReport-Status, Fingerprint, nichtleeres Log und `p4_8_a4_pair_completed` bewertet; diese sind fuer beide Pairs erfuellt.

## Entscheidung

READY_FOR_20_PAIR_RUN = yes

Beide vorgeschriebenen Kontrollpairs sind erfolgreich. Das Hauptfeld `transcript` beschreibt jetzt das Final-Video, nutzt `final.mp4` als Quelle, hat `scope = "viewer_final_transcript"` und enthaelt keinen `raw_mixed_audio`-Pfad mehr.
