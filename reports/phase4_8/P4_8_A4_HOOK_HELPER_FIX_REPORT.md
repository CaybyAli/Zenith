# P4.8-A4 Hook Helper Fix Report

## Status

READY_FOR_20_PAIR_RUN = yes

Bulk wurde nicht gestartet. A5/B1/B2 wurden nicht gestartet. Kein Commit wurde erstellt.

## Ursache

`pair_002` scheiterte zuvor in `base_fingerprint_write`, weil die Final-Hook-Transkription `learning_corpus\pairs\pair_002\final.mp4` direkt an den Helper gab und der native Helper-Prozess mit Returncode `3221226505` abbrach.

Die Diagnose zeigt: `final.mp4` ist lesbar. Der Crash liegt nicht an einer unlesbaren Final-Datei oder an der ffmpeg-Audioextraktion, sondern im nativen Transkriptionspfad beim 30s-Hook-Input.

## Geaenderte Dateien

- `scripts/p4_8_a4_reingest_pairs.py`
- `reports/phase4_8/P4_8_A4_HOOK_HELPER_FIX_REPORT.md`
- `reports/phase4_8/PROGRESS_P4_8.md`

## Neue robuste Hook-Pipeline

- Stage `final_hook_audio_extract`: extrahiert aus `final.mp4` nachvollziehbare Hook-WAVs mit 30s, 20s und 10s.
- WAV-Format: mono, 16 kHz, `pcm_s16le`.
- Stage `final_hook_transcript`: transkribiert ausschliesslich diese WAVs als isolierte Subprozesse.
- Helper-Details werden je Versuch gespeichert: returncode, stdout/stderr tail, Helper-Output, Input-Pfad, Clip-Laenge.
- Retry-Reihenfolge: 30s -> 20s -> 10s.
- Kein Raw-Fallback fuer `hook.first_words`.
- Wenn alle Versuche scheitern, faellt das Pair mit `failed_stage = final_hook_transcript` durch.
- Der Bulk-Harness wertet ein Pair nur als erfolgreich, wenn das Log den `p4_8_a4_pair_completed`-Marker enthaelt.

## Diagnose pair_002 final.mp4

`learning_corpus\pairs\pair_002\final.mp4`:

- Existiert: ja
- Dauer: 592.033333s
- Audio stream: index 0, `aac`, 48000 Hz, 2 channels
- Video stream: index 1, `h264`

Manuelle 30s-WAV-Extraktion:

- Pfad: `reports\phase4_8\debug_pair_002_final_hook_30s.wav`
- Ergebnis: success
- Groesse: 960078 Bytes
- ffprobe WAV: `pcm_s16le`, 16000 Hz, mono, 30.000000s

## Testergebnisse

- `python -m py_compile scripts\p4_8_a4_reingest_pairs.py` -> PASS
- `pair_002_hook_helper_fix` -> SUCCESS nach 20s-Retry
- `pair_001_hook_helper_fix` -> SUCCESS mit 30s-Versuch

Hinweis: Die PowerShell/Tee-Ausgabe enthaelt MediaPipe/TFLite-Stderr als `NativeCommandError`-Text. Die A4-Erfolgskriterien werden ueber PairReport-Status, Fingerprint, nichtleeres Log und `p4_8_a4_pair_completed` bewertet; diese sind fuer beide Pairs erfuellt.

## pair_002 Ergebnis

- Fingerprint: `learning_corpus\pairs\pair_002\style_fingerprint.json`
- Pair-Report: `reports\phase4_8\p4_8_a4_pair_reports\pair_002_hook_helper_fix.json`
- Log: `reports\phase4_8\p4_8_a4_logs\pair_002_hook_helper_fix.log`
- Completed Marker: ja
- Reportstatus: `ok`
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: vorhanden
- `hook.source`: `final`
- `hook.source_path`: `learning_corpus\pairs\pair_002\final.mp4`
- `hook.audio_extract_path`: `reports\phase4_8\hook_debug\pair_002_pair_002_hook_helper_fix_20s_final_hook.wav`
- `hook.analysis_window_seconds`: 30.0
- `hook.effective_window_seconds`: 20.0
- `hook.first_words` vorhanden: ja, 95 Zeichen
- `hook.transcript_attempt_count`: 2
- Versuch 1: 30s WAV, returncode `3221226505`, sauber reportet
- Versuch 2: 20s WAV, returncode `0`, success
- Warning im Report: `final_hook_transcript_retried_with_shorter_window`
- `p4_8_a4_style_capture_source`: `learning_corpus\pairs\pair_002\final.mp4`
- Source-Audit: ok
- Quality-Failed: keine

## pair_001 Ergebnis

- Fingerprint: `learning_corpus\pairs\pair_001\style_fingerprint.json`
- Pair-Report: `reports\phase4_8\p4_8_a4_pair_reports\pair_001_hook_helper_fix.json`
- Log: `reports\phase4_8\p4_8_a4_logs\pair_001_hook_helper_fix.log`
- Completed Marker: ja
- Reportstatus: `ok`
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: vorhanden
- `hook.source`: `final`
- `hook.source_path`: `learning_corpus\pairs\pair_001\final.mp4`
- `hook.audio_extract_path`: `reports\phase4_8\hook_debug\pair_001_pair_001_hook_helper_fix_30s_final_hook.wav`
- `hook.analysis_window_seconds`: 30.0
- `hook.effective_window_seconds`: 30.0
- `hook.first_words` vorhanden: ja, 111 Zeichen
- `hook.transcript_attempt_count`: 1
- Versuch 1: 30s WAV, returncode `0`, success
- `p4_8_a4_style_capture_source`: `learning_corpus\pairs\pair_001\final.mp4`
- Source-Audit: ok
- Quality-Failed: keine

## Korpus-Stand

- `learning_corpus\pairs`: 2 `style_fingerprint.json`
- `learning_corpus\top_solo`: 30 `style_fingerprint.json`
- `learning_corpus\vlogs`: 3 `style_fingerprint.json`

## Entscheidung

READY_FOR_20_PAIR_RUN = yes

Beide vorgeschriebenen Kontrollpairs sind nach identischer Hook-Helper-Logik erfolgreich. Der 30s-native Crash bei `pair_002` wird isoliert und im Report festgehalten; der kontrollierte 20s-Final-WAV-Retry liefert einen validen Final-Hook ohne Raw-Fallback.
