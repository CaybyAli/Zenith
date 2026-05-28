# P4.8-A4 Failure Diagnosis

## Status

STOPP fuer P4.8-A4. Keine A5/B1/B2-Subphase wurde gestartet.

## Kurzbefund

- `scripts/extend_p4_6_fingerprints.py` akzeptiert keine `--pair`- oder `--force-regenerate`-Argumente.
- Der vorhandene P4.6-Extender erweitert nur bereits vorhandene `style_fingerprint.json`-Dateien, erzeugt aber keine neuen Pair-Fingerprints.
- Der aktuelle A4-Harness `scripts/p4_8_a4_reingest_pairs.py` ist fuer den 20-Pair-Lauf nicht belastbar: der Child-Prozess kann vor Report-Erzeugung enden, und alte Logs enthalten kein klares Erfolgs-Signal.
- Der kontrollierte `pair_001`-Einzeltest ist fehlgeschlagen: kein Pair-Fingerprint, kein Pair-Report, kein `completed` im Log.

## Gepruefte Punkte

### 1. `extend_p4_6_fingerprints.py --help`

Ergebnis:

```text
usage: extend_p4_6_fingerprints.py [-h] [--corpus-root CORPUS_ROOT]
                                   [--sample-rate-fps SAMPLE_RATE_FPS]
                                   [--max-samples MAX_SAMPLES] [--limit LIMIT]
                                   [--missing-only] [--report REPORT]
```

Unterstuetzte Optionen:

- `--corpus-root`
- `--sample-rate-fps`
- `--max-samples`
- `--limit`
- `--missing-only`
- `--report`

Nicht unterstuetzt:

- `--pair`
- `--force-regenerate`

### 2. Kontrollierter falscher Aufruf

Command:

```powershell
python scripts\extend_p4_6_fingerprints.py --pair pair_001 2>&1 | Tee-Object debug_pair_001.log
```

Ergebnis:

```text
extend_p4_6_fingerprints.py: error: unrecognized arguments: --pair pair_001
```

Debug-Log: `debug_pair_001.log`

### 3. Pair-Inputs fuer `pair_001`

Alle erwarteten Dateien existieren:

| Datei | Groesse |
|---|---:|
| `learning_corpus/pairs/pair_001/raw.mp4` | 30450563604 Bytes |
| `learning_corpus/pairs/pair_001/raw_mixed_audio.mp4` | 30428443106 Bytes |
| `learning_corpus/pairs/pair_001/final.mp4` | 9351804051 Bytes |
| `learning_corpus/pairs/pair_001/meta.json` | 252 Bytes |

`LearningCorpusIngestor.prepare_video_folder(pair_001)` waehlt korrekt:

```text
prepared_path=learning_corpus/pairs/pair_001/raw_mixed_audio.mp4
audio_stream_count=4
mixed=True
skipped_existing=True
```

Damit ist `raw_mixed_audio.mp4` nicht das fehlende Input-Problem.

### 4. Timeout / Prozessverhalten

Der kontrollierte Einzeltest wurde ohne internen 30-Minuten-Subprozess-Abbruch gestartet:

```powershell
python -u scripts\p4_8_a4_reingest_pairs.py --pair pair_001 --power-profile performance --single-report reports\phase4_8\p4_8_a4_pair_reports\pair_001_control.json 2>&1 | Tee-Object reports\phase4_8\p4_8_a4_logs\pair_001_control.log
```

Ergebnis:

- Exitcode: 1
- Laufzeit: ca. 577 Sekunden
- Log: `reports/phase4_8/p4_8_a4_logs/pair_001_control.log`, 74 Bytes
- Log-Inhalt: nur `p4_8_a4_pair_started pair=pair_001`
- Kein `completed`
- Kein Pair-Report JSON
- Kein `learning_corpus/pairs/pair_001/style_fingerprint.json`

Der Lauf stirbt damit vor dem Python-seitigen Report-Pfad. Wahrscheinlichster Abschnitt ist der Base-Ingest vor der ersten Fingerprint-Schreibung, insbesondere die Transkriptionsphase:

```text
WhisperRuntimeConfig(model_name_or_path='medium', device='auto', compute_type='auto', power_profile='performance')
```

Frueherer `pair_001_attempt1.log` zeigt nur HuggingFace/faster-whisper-Initialisierung, aber kein Abschluss-Signal.

### 5. Wurde `style_fingerprint.json` woanders geschrieben?

Suche nach neu geschriebenen Fingerprints:

```powershell
Get-ChildItem D:\Zenith -Recurse -Filter "style_fingerprint.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-3) }
```

Ergebnis:

```text
recent_count=0
```

Aktueller Korpus-Stand:

| Bereich | style_fingerprint.json |
|---|---:|
| `learning_corpus/pairs` | 0 |
| `learning_corpus/top_solo` | 30 |
| `learning_corpus/vlogs` | 3 |

## Erfolgskriterien fuer `pair_001`

| Kriterium | Ergebnis |
|---|---|
| `learning_corpus/pairs/pair_001/style_fingerprint.json` existiert und ist valide JSON | FAILED, Datei fehlt |
| Pair-Report JSON existiert, nicht 0 Bytes, lesbar | FAILED, Datei fehlt |
| Pair-Log nicht 0 Bytes und enthaelt `completed` oder analoges Erfolgssignal | FAILED, Log ist 74 Bytes, aber ohne `completed` |

`pair_001` gilt damit als FAILED.

## Ursache

Die A4-Orchestrierung ist fehlerhaft:

1. Der urspruenglich naheliegende/angegebene Aufruf `extend_p4_6_fingerprints.py --pair ...` ist ungueltig.
2. Der P4.6-Extender ist kein Base-Ingestor; er kann keine geloeschten Pair-Fingerprints neu erzeugen.
3. Der aktuelle A4-Harness schreibt Reports erst nach erfolgreichem Child-Abschluss. Wenn der Prozess in der Base-Ingest-/Whisper-Phase stirbt, bleiben 0-Byte- oder Start-only-Logs und es entstehen keine Pair-Reports.

Betroffene Datei/Funktionen:

- `scripts/p4_8_a4_reingest_pairs.py`
- `run_pair_subprocess`
- `ingest_single_pair`
- indirekt `core.learning_corpus_ingestor.LearningCorpusIngestor.ingest_video_folder`
- indirekt `core.learning_corpus_transcript.extract_transcript`

## Naechster Fix

Vor einem erneuten A4-Lauf muss der Re-Ingest in kontrollierte, reportende Stages zerlegt werden:

1. Pair-Einzelmodus mit harten Stage-Markern: `prepare_audio`, `transcript`, `base_fingerprint_write`, `p4_6_extension`, `p4_7_repairs`, `style_capture`, `final_audit`.
2. Fehler-Report sofort pro Stage schreiben, nicht erst am Ende.
3. Kein 20-Pair-Loop, bevor `pair_001` und `pair_002` jeweils alle drei Erfolgskriterien erfuellen.
4. Transkriptionsphase fuer den A4-Reingest entkoppeln oder begrenzen, damit `faster-whisper medium` nicht den gesamten 30-GB-Input vor dem ersten Report blockiert.
5. Danach erst `pair_001` kontrolliert wiederholen; bei Erfolg `pair_002`; erst danach 20-Pair-Lauf.

