# P4.8-A4 Fix Report

## Status

READY_FOR_20_PAIR_RUN = yes

Der 20-Pair-Lauf wurde noch nicht gestartet.
Keine A5/B1/B2-Subphase wurde gestartet.

## Ursache

Der A4-Reingest war NO-GO, weil die Orchestrierung auf eine falsche Annahme gebaut war:

- `scripts/extend_p4_6_fingerprints.py` akzeptiert kein `--pair` und kein `--force-regenerate`.
- Der P4.6-Extender erzeugt keine Base-Fingerprints, sondern erweitert nur vorhandene `style_fingerprint.json`.
- Der alte A4-Harness schrieb Reports erst nach erfolgreichem Child-Abschluss. Dadurch konnten Native/Whisper-Abbrueche oder harte Prozessenden ohne Pair-Report und mit 0-Byte-Logs erscheinen.
- `LearningCorpusIngestor.ingest_video_folder()` transkribierte vor der ersten Fingerprint-Schreibung den grossen `raw_mixed_audio.mp4` unbounded mit faster-whisper `medium`.

## Geaenderte Dateien

- `scripts/p4_8_a4_reingest_pairs.py`
- `reports/phase4_8/P4_8_A4_FAILURE_DIAGNOSIS.md`
- `reports/phase4_8/PROGRESS_P4_8.md`
- `reports/phase4_8/P4_8_A4_FIX_REPORT.md`

## Neue Schutzmechanismen

- `--pair <name>` und `--single-report <path>` funktionieren ohne ungueltige P4.6-CLI-Argumente.
- Jeder Pair-Lauf schreibt sofort einen JSON-Report.
- Jeder Stage-Start und jedes Stage-Ende wird geloggt und in den Report geschrieben.
- Bei Python-Exceptions schreibt der Report `status=failed`, `failed_stage`, `exception_type`, `exception_message`, gekuerztes `traceback`, `started_at`, `finished_at` und `duration_seconds`.
- Transcript laeuft bounded in einem Helper-Subprozess:
  - Audio-Clip: 75 Sekunden
  - Modell: `tiny` per Default, ueberschreibbar via `ZENITH_P4_8_A4_TRANSCRIPT_MODEL`
  - Timeout: 600 Sekunden
  - Bei Helper-Fehler/Timeout wird ein expliziter Placeholder-Transcript geschrieben statt still zu crashen.
- Bulk-Lauf ist gegen Blindstart gesperrt und erfordert `--allow-bulk`.
- Top-Solo und Vlogs werden im Pair-Einzelmodus nicht angefasst.

## py_compile

Command:

```powershell
python -m py_compile scripts\p4_8_a4_reingest_pairs.py
```

Ergebnis: PASS, Exitcode 0.

## pair_001 Kontrolltest

Command:

```powershell
python -u scripts\p4_8_a4_reingest_pairs.py --pair pair_001 --power-profile performance --single-report reports\phase4_8\p4_8_a4_pair_reports\pair_001_fix_control.json 2>&1 | Tee-Object reports\phase4_8\p4_8_a4_logs\pair_001_fix_control.log
```

Ergebnis: SUCCESS.

| Artefakt | Pfad | Groesse |
|---|---|---:|
| Fingerprint | `learning_corpus/pairs/pair_001/style_fingerprint.json` | 9669 Bytes |
| Pair-Report | `reports/phase4_8/p4_8_a4_pair_reports/pair_001_fix_control.json` | 7792 Bytes |
| Log | `reports/phase4_8/p4_8_a4_logs/pair_001_fix_control.log` | 22594 Bytes |

Stage-Ergebnis:

| Stage | Status | Dauer |
|---|---|---:|
| prepare_audio | ok | 0s |
| transcript | ok | 20s |
| base_fingerprint_write | ok | 578s |
| p4_6_extension | ok | 359s |
| p4_7_repairs | ok | 0s |
| style_capture | ok | 0s |
| final_audit | ok | 0s |

Log-Beweis:

```text
p4_8_a4_pair_completed pair=pair_001
```

Fingerprint-Audit:

- Valide JSON: ja
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: ja
- Report `status`: `ok`

## pair_002 Kontrolltest

Command:

```powershell
python -u scripts\p4_8_a4_reingest_pairs.py --pair pair_002 --power-profile performance --single-report reports\phase4_8\p4_8_a4_pair_reports\pair_002_fix_control.json 2>&1 | Tee-Object reports\phase4_8\p4_8_a4_logs\pair_002_fix_control.log
```

Ergebnis: SUCCESS.

| Artefakt | Pfad | Groesse |
|---|---|---:|
| Fingerprint | `learning_corpus/pairs/pair_002/style_fingerprint.json` | 10651 Bytes |
| Pair-Report | `reports/phase4_8/p4_8_a4_pair_reports/pair_002_fix_control.json` | 6725 Bytes |
| Log | `reports/phase4_8/p4_8_a4_logs/pair_002_fix_control.log` | 19866 Bytes |

Stage-Ergebnis:

| Stage | Status | Dauer |
|---|---|---:|
| prepare_audio | ok | 0s |
| transcript | ok | 9s |
| base_fingerprint_write | ok | 444s |
| p4_6_extension | ok | 271s |
| p4_7_repairs | ok | 0s |
| style_capture | ok | 0s |
| final_audit | ok | 0s |

Log-Beweis:

```text
p4_8_a4_pair_completed pair=pair_002
```

Fingerprint-Audit:

- Valide JSON: ja
- Pflichtfelder `audio`, `transcript`, `facial_expression_distribution`: ja
- Report `status`: `ok`

## Korpus-Stand nach Fix-Kontrolltests

| Bereich | style_fingerprint.json |
|---|---:|
| `learning_corpus/pairs` | 2 |
| `learning_corpus/top_solo` | 30 |
| `learning_corpus/vlogs` | 3 |

## Entscheidung

READY_FOR_20_PAIR_RUN = yes

Begruendung: `pair_001` und `pair_002` sind einzeln erfolgreich durch alle A4-Stages gelaufen, inklusive Fingerprint, Report und Completed-Log. Der naechste Schritt darf der 20-Pair-A4-Lauf mit explizitem `--allow-bulk` sein.

