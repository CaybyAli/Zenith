# GO / NO-GO LOG

Stand: 2026-06-09

Aktuelle Entscheidungslage: Phase 5 ist FINAL GO. P5-L ist 100% / CLOSED. Runtime Learning Gate bleibt NO-GO bis Master-GO. Phase 5.5 Musik ist 100% / Final Audit GO. Controlled Preview Run ist separater Owner/Master-GO-Gate. Musik-Build, echter Audio-Mix und echter Render bleiben NO-GO bis eigenes Master-GO. Uncut-Musik ist dauerhaft NO-GO.

## Phase 5 FINAL GO

Entscheidung: GO.

Begruendung:
- Alle 8 Phase-5-Endkriterien sind DONE.
- K7 echter Kontroll-Run + Ali-Freigabe ist DONE.
- Blocker: keine.

Grenzen:
- Phase 5.5 wurde dadurch NICHT gestartet.
- P5-L wurde als eigener Post-Phase-5-Bereich gestartet.

## P5-L0 Opening-Doku GO

Entscheidung: GO fuer Dokumentation und Schutzregeln.

NO-GO:
- echter Learning-Loop
- Overnight/Dauerlernen
- Qwen-Autocut
- Phase 5.5 Musik

## P5-L2 FINAL GO

Entscheidung: GO.

Beweis:
- Code/Test Commit: `af5a89c`.
- Mini-run: `status=ok`.
- Reports: nicht committed.

Weiterhin NO-GO:
- echter Learning-Loop
- Phase 5.5 Musik

## P5-L3 FINAL GO

Entscheidung: GO.

Beweis:
- Code/Test Commit: `361505d`.
- Pytest: 8 passed.
- Mini-run: `status=ok`.
- Output blieb Reports-only.

## P5-L4 FINAL GO

Entscheidung: GO.

Beweis:
- Feature Commit: `1244f4c`.
- Cleanup Commit: `aa04a99`.
- Pytest: 10 passed.
- Qwen blieb `analysis_only`.
- Qwen blieb `can_cut=false`.

NO-GO:
- Qwen-Autocut
- Render
- Ingest
- Musik
- Phase 5.5

## P5-L5 FINAL GO

Entscheidung: GO fuer bounded dry-run.

Beweis:
- Code/Test Commit: `e0768b4`.
- Pytest: 9 passed.
- Mini-run: `status=ok`.

Grenzen:
- Kein echter Overnight-Dauerlauf.
- Kein echter Learning-Loop.

## P5-L6 FINAL GO

Entscheidung: GO.

Beweis:
- Feature Commit: `37bd5f8`.
- Cleanup Commit: `45f57f1`.
- Pytest: 8 passed.
- Mini-run: `status=ok`.
- Ali Owner Review: GO.

Grenzen:
- P5-L7 wurde NICHT gestartet.
- Phase 5.5 blieb locked.

## P5-L6.5 Gruppe 5B FINAL GO

Entscheidung: GO.

Beweis:
- Code/Test Commit: `19e16d2`.
- Full Hash: `19e16d2b2423ba7ee188021c5fb338a2ee0ce93a`.
- Zieltests: 33 passed.
- Mini-Runs P5-L2/P5-L4/P5-L6: `status=ok`.

Fixes:
- P5-L6 Owner-GO maschinenlesbar im Manifest.
- P5-L4 core Importproblem behoben.
- P5-L2 Output Guard gehaertet.

## P5-L6.5 Gruppe 5C Obsidian Cleanup

Entscheidung: GO-faehig, wenn Scope sauber bleibt und Commit remote ist.

Erlaubt:
- Obsidian aktualisieren.
- Truth Store konsolidieren.
- Index- und Runbook-Dateien erstellen.

NO-GO:
- Code aendern.
- Tests aendern.
- Reports committen.
- Qwen starten.
- Render/Ingest/Musik starten.
- P5-L7 starten.
- Phase 5.5 starten.

## P5-L6.5 Gruppe 5D FINAL GO

Entscheidung: GO.

Beweis:
- Code/Test Commit: `a3af5e3`.
- Full Hash: `a3af5e3c8548bb9240e0377b3c8a2263796bbcc8`.
- Modell: `qwen3.6:latest`.
- `qwen_requested=true`.
- `qwen_used=true`.
- `qwen_visible_response=true`.
- `qwen_role=analysis_only`.
- `qwen_can_cut=false`.
- `qwen_autocut_allowed=false`.
- `dangerous_response_detected=false`.

Grenzen:
- Echter Learning-Loop wurde NICHT gestartet.
- P5-L7 bleibt NO-GO bis Master-GO.
- Phase 5.5 Musik bleibt locked.

## P5-L6.5 Gruppe 5E Dokumentations-GO

Entscheidung: GO fuer Abschlussbericht / Final Audit und Claude Senior Handoff.

Beweis:
- `obsidian_zenith/07_PostPhase5_Learning/P5L_Final_Audit_Report.md`
- `obsidian_zenith/07_PostPhase5_Learning/Claude_Senior_Handoff.md`

Grenzen:
- Kein Code.
- Keine Reports committed.
- Kein Qwen gestartet.
- Kein Render.
- Kein Ingest.
- Keine Musik.
- Kein echter Learning-Loop.

## P5-L6.5 Gruppe 5F P5-L CLOSE FINAL GO

Entscheidung: GO.

Beweis:
- Option B dokumentiert.
- `obsidian_zenith/07_PostPhase5_Learning/P5L_Close_Report.md`
- `obsidian_zenith/07_PostPhase5_Learning/Runtime_Learning_Gate.md`

Ergebnis:
- P5-L ist 100% / CLOSED.
- P5-L wurde als Vorbereitung abgeschlossen.
- P5-L7 / Schlaf-Learning-Run ist spaeteres Runtime Learning Gate / later / locked.

Grenzen:
- Echter Learning-Run bleibt NO-GO bis Runtime-Gate mit Master-GO.
- Phase 5.5 Musik bleibt locked bis Opening-Gate mit Master-GO.
- Kein Code.
- Keine Reports committed.
- Kein Qwen gestartet.
- Kein Render.
- Kein Ingest.
- Keine Musik.

## Naechster Gate

Controlled Music Preview Run nur nach separatem Master-GO und Owner Review.

Weiterhin NO-GO:
- Runtime Learning Gate / echter Learning-Loop.
- Musik-Build.
- Echter Audio-Mix.
- Uncut-Musik.
- Preview-Render.
- Qwen-Autocut.

## Phase 5.5 Opening-Gate GO

Entscheidung: GO fuer Obsidian-Opening-Gate / Planungsbereich.

Beweis:
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Opening_Gate.md`
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Safety_Rules.md`
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Backlog.md`
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Run_Log.md`

Ergebnis:
- Phase 5.5 Musik: 5% / Opening-Gate.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-1 Musik-Inventory.

Grenzen:
- Kein Code.
- Keine Reports committed.
- Kein Render.
- Kein Ingest.
- Keine Musik gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.

## Phase 5.5-1 Musik-Inventory GO

Entscheidung: GO fuer Obsidian-Inventory / lokale Musikquellen-Pruefung.

Beweis:
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Music_Inventory.md`
- `obsidian_zenith/08_Phase5_5_Music/Phase5_5_Music_Library_Rules.md`

Ergebnis:
- Phase 5.5 Musik: 15% / Musik-Inventory.
- Lokale Musik-Kandidaten gefunden, aber nicht verwendet.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-2 Musik-Contracts / Manifest + Safety-Flags.

Grenzen:
- Kein Code.
- Keine Reports committed.
- Keine Musikdateien erzeugt, kopiert oder committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-4A Lokale Main-Musikordner GO

Entscheidung: GO fuer lokale Ordner-Vorbereitung.

Beweis:
- Ordner unter `local_assets/music/main_account/` erstellt.
- Kategorien: `intro`, `funny`, `suspense`, `calm`, `hype`, `victory`, `emotional`, `background`, `peak`, `outro`.
- Diese Kategorie-Liste ist durch 5.5-4A-R superseded.
- `.gitignore` ignoriert `local_assets/music/`.

Ergebnis:
- Ali kann spaeter manuell Epidemic-Sound-Musik einsortieren.
- Uncut-Musik bleibt dauerhaft NO-GO.
- Kein `local_assets/music/uncut` erstellt.
- Keine Musikdateien erzeugt oder kopiert.
- Musikdateien bleiben lokal und werden nicht committed.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Schritt: 5.5-4B Musikordner-Verifikation nach manuellem Befuellen.

Grenzen:
- Kein Code.
- Keine Tests.
- Keine Reports committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-4A-R Ali-Musikordner-Taxonomie GO

Entscheidung: GO fuer Code-/Test-Patch und Obsidian-Dokumentation der echten Ali-Ordnerstruktur.

Beweis:
- Code Commit: `ce0af0c`
- Full Hash: `ce0af0c1787cc0d266b4cbeb837d8f91130aacdb`
- `core/music_contracts.py`
- `core/music_energy_mapping.py`
- `core/music_selector.py`
- `scripts/p55_music_contracts_smoke.py`
- `scripts/p55_energy_to_music_mapping_smoke.py`
- `scripts/p55_music_selector_smoke.py`
- `tests/test_p55_music_contracts.py`
- `tests/test_p55_energy_to_music_mapping.py`
- `tests/test_p55_music_selector.py`

Ergebnis:
- Neue offizielle Kategorien: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- `hype` bedeutet spannend / Action / Peak / Clutch.
- `suspense` wird als Mood auf `hype` gemappt.
- `calm`, `neutral`, default gameplay mappen auf `vlog_background`.
- `funny` mappt auf `funny_gaming_background`.
- `fail` und `sad` mappen direkt.
- Uncut bleibt dauerhaft NO-GO: `music_allowed=false`, `category=none`.
- Pytest: 53 passed.
- Smoke Runs: `status=ok`.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-4B Musikordner-Verifikation nach manuellem Einsortieren.

Grenzen:
- Keine Musikdateien gelesen, erzeugt, kopiert, verschoben oder committed.
- Alte Ordner wurden nicht geloescht und nicht verschoben.
- Reports nicht committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-3R Main/Uncut Mood Patch GO

Entscheidung: GO fuer Main-only Musikregel und Mood-Kategorien.

Beweis:
- Code Patch Commit: `cf75021`
- Full Hash: `cf750216e75f458bd2db670b44387adb4bd1032a`
- `core/music_contracts.py`
- `core/music_energy_mapping.py`
- `scripts/p55_music_contracts_smoke.py`
- `scripts/p55_energy_to_music_mapping_smoke.py`
- `tests/test_p55_music_contracts.py`
- `tests/test_p55_energy_to_music_mapping.py`
- Patch Manifest: `reports/phase5_5_main_uncut_mood_patch/main_uncut_mood_patch_manifest.json`

Ergebnis:
- Main Account Musik: spaeter erlaubt, nur mit Safety/Owner/Lizenz/Manifest.
- Uncut-Musik: dauerhaft NO-GO.
- Uncut Mapping: `music_allowed=false`, `music_category=none`.
- Channel Rules: enforced.
- Damalige Mood-Kategorien sind durch 5.5-4A-R superseded.
- Pytest: 35 passed.
- Smoke Runs: `status=ok`.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-4 Musik-Selector.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert, ausgewaehlt oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-4 Musik-Selector GO

Entscheidung: GO fuer reine Main-Account-Metadaten-Selektion.

Beweis:
- Code Commit: `7ca03f0`
- Full Hash: `7ca03f0e8806253d787d03b58e9cfa7d0aa75f69`
- `core/music_selector.py`
- `scripts/p55_music_selector_smoke.py`
- `tests/test_p55_music_selector.py`
- Smoke Manifest: `reports/phase5_5_music_selector/music_selector_manifest.json`

Ergebnis:
- Phase 5.5 Musik: 60% / Musik-Selector.
- Main Account Selector vorhanden.
- Uncut-Musik bleibt dauerhaft NO-GO.
- Missing Category: `missing_candidate`, kein Fallback.
- Pytest: 16 passed.
- Smoke Run: `status=ok`.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-5 Ducking Plan.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien gelesen, erzeugt, kopiert, ausgewaehlt oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-2 Musik-Contracts GO

Entscheidung: GO fuer Code-Safety-Baustein / Contracts / Manifest-Struktur.

Beweis:
- Code/Safety Commit: `6e536ea`
- Full Hash: `6e536ea130134405505820dae3a9c23b898550a4`
- `core/music_contracts.py`
- `scripts/p55_music_contracts_smoke.py`
- `tests/test_p55_music_contracts.py`
- Smoke Manifest: `reports/phase5_5_music_contracts/music_contracts_manifest.json`

Ergebnis:
- Phase 5.5 Musik: 30% / Musik-Contracts.
- Pytest: 10 passed.
- Smoke Run: `status=ok`.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-3 Energy-to-Music Mapping.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-3 Energy-to-Music Mapping GO

Entscheidung: GO fuer reine Mapping-Logik.

Beweis:
- Code Commit: `c14575d`
- Full Hash: `c14575d68fd91c4bfcef77b7757d81bdd0a6e216`
- `core/music_energy_mapping.py`
- `scripts/p55_energy_to_music_mapping_smoke.py`
- `tests/test_p55_energy_to_music_mapping.py`
- Smoke Manifest: `reports/phase5_5_energy_to_music_mapping/energy_to_music_mapping_manifest.json`

Ergebnis:
- Phase 5.5 Musik: 45% / Energy-to-Music Mapping.
- Pytest: 14 passed.
- Smoke Run: `status=ok`.
- Mapping plant Kategorien, waehlt aber keine Musikdatei aus.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-4 Musik-Selector.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert, ausgewaehlt oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-4B Lokale Main-Musikbibliothek GO

Entscheidung: GO fuer lokale Musikordner-Sicherheit / Git-Schutz / Main-Account-Bibliothek.

Beweis:
- Offizielle Kategorien geprueft: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- Anzahl Musikdateien gesamt: 87.
- Anzahl pro Ordner: `intro=4`, `outro=5`, `vlog_background=8`, `funny_gaming_background=34`, `fail=15`, `hype=15`, `sad=6`.
- Anzahl pro Endung: `.mp3=87`, `.wav=0`, `.flac=0`, `.m4a=0`, `.aac=0`, `.ogg=0`, `.opus=0`.
- `local_assets/music/uncut` existiert nicht.
- `git status --ignored --short -- local_assets/music`: `!! local_assets/music/`.
- `git ls-files local_assets/music`: leer.
- Report: `reports/phase5_5_music_folder_verification/music_folder_verification_summary.md`.

Ergebnis:
- Phase 5.5 Musik: 60% / lokale Main-Musikbibliothek verifiziert.
- Musikdateien bleiben lokal und ignored.
- Keine Musikdateien tracked.
- Keine Musikdateien staged.
- Keine Musikdateien committed.
- Musik-Build weiterhin NO-GO.
- Preview-Render weiterhin NO-GO.
- Runtime Learning Gate weiterhin locked / later.
- Naechster Gate: 5.5-5 Ducking Plan / Audio-Mix Safety.

Grenzen:
- Keine Musikdateien geoeffnet.
- Keine Musikdateien gelesen.
- Keine Musikdateien abgespielt.
- Keine Musikdateien kopiert.
- Keine Musikdateien geloescht.
- Keine Musikdateien konvertiert.
- Kein Render.
- Kein Preview-Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-5 Ducking Plan GO

Entscheidung: GO fuer reine Ducking-Planung / Audio-Mix-Safety.

Beweis:
- Code Commit: `80e361f`
- Full Hash: `80e361f753d77c44eab1c0708a30e744c8cf6671`
- `core/music_ducking_plan.py`
- `scripts/p55_ducking_plan_smoke.py`
- `tests/test_p55_ducking_plan.py`
- Smoke Manifest: `reports/phase5_5_ducking_plan/ducking_plan_manifest.json`

Ergebnis:
- Phase 5.5 Musik: 75% / Ducking Plan abgeschlossen.
- Main Account Ducking Plan vorhanden.
- Ali/Friend-Stimmen haben Vorrang.
- Uncut-Musik bleibt NO-GO.
- Missing Candidate erzeugt `no_selected_music`.
- `max_music_gain_db` darf nie lauter als `-14.0` werden.
- Pytest: 17 passed.
- Smoke Run: `status=ok`.
- Musik-Build weiterhin NO-GO.
- Echter Audio-Mix weiterhin NO-GO.
- Naechster Gate: 5.5-6 Controlled Music Preview Gate.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien gelesen, geoeffnet, erzeugt, kopiert, geloescht, konvertiert oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Preview-Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-6 Controlled Music Preview Gate GO

Entscheidung: GO fuer reine Gate-Validierung / Controlled Preview Safety.

Beweis:
- Code Commit: `fada35c`
- Full Hash: `fada35cdfb25f1a142d752ce93a4e8984884eecb`
- `core/music_preview_gate.py`
- `scripts/p55_music_preview_gate_smoke.py`
- `tests/test_p55_music_preview_gate.py`
- Smoke Manifest: `reports/phase5_5_music_preview_gate/music_preview_gate_manifest.json`

Ergebnis:
- Phase 5.5 Musik: 90% / Controlled Music Preview Gate abgeschlossen.
- Main Account Preview Gate vorhanden.
- Owner Preview GO ist Pflicht.
- Main clean gate wird `ready_for_controlled_preview`.
- Ready for controlled preview ist kein automatischer Render und kein Audio-Mix.
- Uncut-Musik bleibt NO-GO.
- Pytest: 21 passed.
- Smoke Run: `status=ok`.
- Musik-Build weiterhin NO-GO bis separater Master-GO.
- Echter Audio-Mix weiterhin NO-GO.
- Naechster Gate: 5.5-7 Final Audit oder kontrollierter Preview-Run.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien gelesen, geoeffnet, erzeugt, kopiert, geloescht, konvertiert oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Preview-Render.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Phase 5.5-7 Final Audit GO

Entscheidung: GO fuer Final Audit / Infrastruktur-Bereitschaft.

Beweis:
- Final Audit Manifest: `reports/phase5_5_final_audit/phase5_5_final_audit_manifest.json`
- Final Audit Summary: `reports/phase5_5_final_audit/phase5_5_final_audit_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 91 passed.
- Alle Phase-5.5-Smoke-Runs: `status=ok`.

Ergebnis:
- Phase 5.5 Musik: 100% / Final Audit GO.
- Contracts ready.
- Mapping ready.
- Selector ready.
- Ducking Plan ready.
- Preview Gate ready.
- Music library verified: 87 MP3-Dateien.
- Main Account Musik nur nach separatem Preview-Run-GO.
- Uncut-Musik bleibt dauerhaft NO-GO.
- Controlled Preview Run bleibt separater Owner/Master-GO-Gate.
- Musik-Build weiterhin NO-GO bis Preview-Run-GO.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien committed.
- Reports nicht committed.
- Kein Render.
- Kein Preview-Render.
- Kein echter Audio-Mix.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Controlled Music Preview Run Schritt 0 Input-Auswahl DIAGNOSE

Entscheidung: GO nur fuer Diagnose / Input-Auswahl, kein Preview-Run.

Beweis:
- Diagnose-Report: `reports/controlled_music_preview_input_selection/input_selection_summary.md`
- Top Empfehlung: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Alternative Main-Account-Pfad: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
- Musikbibliothek: `local_assets/music/` ignored, `git ls-files local_assets/music` leer.

Ergebnis:
- Controlled Music Preview Run: Input-Auswahl vorbereitet.
- Ali muss einen Input-Kandidaten bestaetigen.
- Schritt 1 bleibt NO-GO bis separatem Master-GO.
- Nur Main Account darf spaeter Musik bekommen.
- Uncut-Musik bleibt dauerhaft NO-GO.

Grenzen:
- Keine Musik eingefuegt.
- Keine Musikdateien geoeffnet, abgespielt, konvertiert oder committed.
- Reports nicht committed.
- Kein Render.
- Kein Preview-Render.
- Kein echter Audio-Mix.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.

## Controlled Music Preview Run Schritt 1 Preview-Plan

Entscheidung: GO fuer reine Preview-Plan-Vorbereitung, kein Musik-Build und kein Render.

Beweis:
- Plan-Manifest: `reports/controlled_music_preview_run/step1_preview_plan/preview_plan_manifest.json`
- Plan-Summary: `reports/controlled_music_preview_run/step1_preview_plan/preview_plan_summary.md`
- Bestaetigter Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Input existiert: ja, `108427404` Bytes, LastWriteTime `2026-06-05 17:50:57`.
- Musikbibliothek: `local_assets/music/` ignored, `git ls-files local_assets/music` leer.
- Main-Account-Musikdateien: 87.

Ergebnis:
- Controlled Music Preview Run: Plan vorbereitet.
- Channel Type: `main`.
- Main Account Musik spaeter erlaubt, nur mit Owner Review und Safety-Gate.
- Uncut-Musik bleibt dauerhaft NO-GO.
- `ducking_required=true`.
- `owner_review_required=true`.
- `upload_allowed=false`.
- `runtime_learning_allowed=false`.
- `qwen_autocut_allowed=false`.
- Naechster Schritt: Controlled Music Preview Run Schritt 2 nur nach Master-GO.

Grenzen:
- Keine Musik eingefuegt.
- Kein Musik-Build gestartet.
- Kein Audio-Mix gestartet.
- Kein Render.
- Kein Preview-Render.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 2 Preview-Render

Entscheidung: GO fuer genau einen kontrollierten Main-Account-Musik-Preview-Render nach Master-GO.

Beweis:
- Code-Commit: `b672dd4` / `b672dd4f413e4537394640379728846ffa6b209a`.
- Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Output-MP4: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/controlled_music_preview_main.mp4`.
- Output-Groesse: `107923180` Bytes.
- Manifest: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/preview_render_manifest.json`.
- Summary: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/preview_render_summary.md`.
- Musik-Kategorie: `vlog_background`.
- Musikdatei: `local_assets/music/main_account/vlog_background/ES_As Daylight Fades - Sulu.mp3`.
- Channel Type: `main`.
- Manifest Status: `ok`.

Ergebnis:
- Controlled Music Preview Run Schritt 2 ausgefuehrt.
- Genau ein neuer kontrollierter Preview-Render wurde erzeugt.
- Owner Review ist jetzt Pflicht.
- Naechster Schritt: Ali Auge/Ohr Review mit GO / FIX / NO-GO.

Grenzen:
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Runtime Learning.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Keine Produktionsdateien geaendert.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.

## Controlled Music Preview Run Schritt 8A Low-Speech-Retune + neue Clip-Kandidaten

Entscheidung: Owner Review Schritt 8 = FIX. Code-GO nur fuer erneutes Low-Speech-Retune und neue Clip-Kandidatensuche, kein Render.

Beweis:
- Code-Commit: `f6725b9` / `f6725b97ec7cbc6bacca873ff366198507b1c987`.
- Geaendert: `core/music_ducking_plan.py`, `scripts/controlled_music_preview_render.py`, `tests/test_p55_ducking_plan.py`, `tests/test_controlled_music_preview_render.py`.
- Lokaler Report: `reports/controlled_music_preview_run/step8a_owner_review_fix_low_speech_new_clip/step8a_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step8a_owner_review_fix_low_speech_new_clip/step8a_summary.md`.
- Dry-Run: `status=dry_run`, kein MP4 erzeugt.

Ergebnis:
- Low-Speech Base Gain: `-27.0`.
- Low-Speech Ducking Gain: `-32.0`.
- Low-Speech Max Gain: `-25.0`.
- Additional reduction: `5.0` dB.
- Total reduction: `10.0` dB.
- Alter K7-Clip wird fuer naechsten Review nicht weiter benutzt.
- Top 3 neue Clip-Kandidaten:
  1. `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
  2. `reports/phase5/g2_s3b_multispeaker_pair001/g2_s3b_pair001_short_1.mp4`
  3. `reports/phase5/g2_s3b_friend_rich_520_540/g2_s3b_friend_rich_520_540_short_1.mp4`
- Naechster Schritt: Controlled Music Preview Schritt 8B neuen Clip auswaehlen nur nach Master-GO.

Grenzen:
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 10B Proper Run Selection

Entscheidung: Ali/Master hat den richtigen `gaming_main` Run fuer den finalen Musik-Review ausgewaehlt. Kein Render-GO in Schritt 10B.

Beweis:
- Ausgewaehlter Run: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Dauer: `520.25s` / ca. 8.67min.
- Groesse: `800312704` Bytes.
- Kein Short, kein raw, kein uncut, kein controlled-preview Output.
- Musik-Tuning fuer Step 11 bleibt `funny_gaming_background`, Intro Offset `30.0s`, Low-Speech Gains `-27.0`, `-32.0`, `-25.0`.
- `vlog_background` bleibt verboten.
- Readiness-Risiko: ausgewaehlter Proper Run und Step-11-Output-Root sind im Controlled-Preview-Script noch nicht erlaubt.
- Report: `reports/controlled_music_preview_run/step10b_select_proper_run/step10b_manifest.json`.

Grenzen:
- Kein Render gestartet.
- Kein Preview-Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Keine Musikdateien committed.
- Reports nicht committed.

Naechster Schritt:
- Controlled Music Preview Step 11 Proper Run Render nur nach Master-GO.
- Wenn Input/Output-Allowlist blockiert: STOPP und Master fragen.

## Controlled Music Preview Run Schritt 11A Proper-Run-Allowlist-Fix

Entscheidung: GO fuer exakt den Step-11A-Allowlist-Fix. Kein Render-GO.

Beweis:
- Code-Commit: `74da7bf` / `74da7bf14f93c1da3bed379cf5ea1232afdab525`.
- Geaendert: `scripts/controlled_music_preview_render.py`, `tests/test_controlled_music_preview_render.py`.
- Proper Run Input erlaubt: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Step-11 Output-Root erlaubt: `reports/controlled_music_preview_run/step11_proper_run_final_music_render`.
- Dry-Run mit Proper Run: `status=dry_run`.
- Pytest: 32 passed.
- Report: `reports/controlled_music_preview_run/step11a_proper_run_allowlist_fix/step11a_manifest.json`.

Ergebnis:
- Schritt 10B Readiness-Blocker ist beseitigt.
- Beliebige `exports` bleiben verboten.
- `reports/controlled_music_preview_run` bleibt als Input verboten.
- `learning_corpus`, `local_assets/music` und `video_configs` bleiben als Input blockiert.
- Kein Fallback auf K7.
- Kein Fallback auf Short.

Grenzen:
- Kein Execute Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

Naechster Schritt:
- Controlled Music Preview Step 11B Proper Run Render nur nach Master-GO.

## Controlled Music Preview Run Schritt 11B Proper Run Final Music Render

Entscheidung: Master-GO fuer genau einen lokalen Proper-Run-Musik-Preview-Render mit finalem Musik-Tuning.

Beweis:
- Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Input-Dauer: `520.250131s` / ca. 8.67min.
- Output-MP4: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/controlled_music_preview_main.mp4`.
- Output-Groesse: `798591899` Bytes.
- Manifest: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/preview_render_manifest.json`.
- Summary: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/preview_render_summary.md`.
- Step-11B-Report: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/step11b_render_manifest.json`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- Channel Type: `main`.
- Content Type: `gaming_main`.
- Manifest Status: `ok`.

Ergebnis:
- Controlled Music Preview Run Schritt 11B ausgefuehrt.
- Echter 8.67-Minuten-Proper-Run wurde lokal mit finalem Musik-Tuning gerendert.
- Alter K7-Clip wurde nicht genutzt.
- Short-Clip wurde nicht genutzt.
- `vlog_background` wurde nicht genutzt.
- `music_start_offset_sec=30.0`.
- `intro_trim_used=true`.
- `intro_boost_used=false`.
- Low-Speech Gains: `-27.0`, `-32.0`, `-25.0`.
- Owner Review Schritt 12 ist jetzt Pflicht.

Grenzen:
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Runtime Learning.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Keine Produktionsdateien geaendert.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.

Naechster Schritt:
- Controlled Music Preview Step 12 Owner Review Proper Run Final Music Tuning.

## Controlled Music Preview Run Schritt 12A Owner NO-GO Diagnosis

Entscheidung: Owner Review Schritt 12 = NO-GO. Step 12A ist reine Diagnose. Kein Code-Fix, kein Render.

Beweis:
- Owner Visual Issue: Output zeigt nur Facecam fullscreen.
- Owner Audio Issue: Musik dauerhaft zu laut, auch bei Sprache/Freunden.
- Diagnose-Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- NO-GO Output: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/controlled_music_preview_main.mp4`.
- Diagnose-Report: `reports/controlled_music_preview_run/step12a_owner_review_no_go_diagnosis/step12a_manifest.json`.
- Diagnose-Summary: `reports/controlled_music_preview_run/step12a_owner_review_no_go_diagnosis/step12a_summary.md`.
- Diagnose-Screenshots: `input_010s.png`, `output_010s.png`, `input_060s.png`, `output_060s.png`, `input_180s.png`, `output_180s.png`, `input_360s.png`, `output_360s.png`.

Ergebnis:
- Input ist Facecam fullscreen: ja.
- Output ist Facecam fullscreen: ja.
- Input-/Output-Frames sind an 10s, 60s, 180s und 360s byte-identisch.
- Visuelle Root Cause: der ausgewaehlte Proper Run ist selbst Facecam fullscreen; Step-11B kopiert das Video unveraendert.
- FFmpeg Video Mapping: `-map 0:v:0` und `-c:v copy`.
- Manifest-Gains vorhanden: ja, `-27.0`, `-32.0`, `-25.0`.
- FFmpeg command nutzt diese Gains direkt: nein; echter Filter nutzt `volume=0.08` plus `sidechaincompress`.
- Speech/Friend-Ducking bestaetigt: nein.
- Audio Root Cause: keine echte transcript-/speaker-/friend-aware Ducking-Kurve bestaetigt; Manifest-Gains stehen nicht direkt im ffmpeg command.

Grenzen:
- Kein Code-Fix.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Keine Musikdateien committed.
- Reports/Screenshots nicht committed.

Naechster Schritt:
- Controlled Music Preview Step 12B Fix after Owner NO-GO nur nach Master-GO.
- Danach erst Dry-Run.
- Kein Execute Render ohne weiteres Master-GO.

## Controlled Music Preview Run Schritt 12B Find Visually Valid Proper Run

Entscheidung: Step-12A-Ergebnis bestaetigt. Kein Video-Mapping-Fix. Step 12B sucht nur visuell gueltige Proper-Run-Kandidaten. Kein Render.

Beweis:
- Alter falscher Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Alter Input war Facecam fullscreen: ja.
- Video-Mapping-Fix noetig: nein.
- Lokaler Report: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/step12b_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/step12b_summary.md`.
- Screenshot-Belege lokal: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/`.

Top 3:
1. `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`
   - Dauer: `528.348813s`.
   - Gameplay sichtbar: ja.
   - Facecam fullscreen: nein.
2. `exports/gaming_main/job_059053a7fa2a/job_059053a7fa2a_v1_final.mp4`
   - Dauer: `528.301729s`.
   - Gameplay sichtbar: ja.
   - Facecam fullscreen: nein.
3. `exports/gaming_main/job_a78b3b182979/job_a78b3b182979_v1_final.mp4`
   - Dauer: `536.401729s`.
   - Gameplay sichtbar: ja.
   - Facecam fullscreen: nein.

Empfehlung:
- `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.

Grenzen:
- Kein Code-Fix.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Keine Musikdateien committed.
- Reports/Screenshots nicht committed.

Audio-Hinweis:
- Manifest-Gains nicht direkt im FFmpeg-Command bestaetigt.
- Speech-aware Ducking nicht bestaetigt.
- Audio-Thema bleibt offen.

Naechster Schritt:
- Controlled Music Preview Step 12C visuell gueltigen Proper Run auswaehlen nur nach Master-GO.
- Noch kein Render.

## Controlled Music Preview Run Schritt 10A Find Proper Run Input

Entscheidung: Owner Review Schritt 10 = Musik-Tuning grundsaetzlich gut, aber Testmedium nicht ausreichend. Kein Render. Nur passenden richtigen Run suchen.

Beweis:
- Nicht als finaler Musik-Beweis nutzen: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render/run_20260610_203039/controlled_music_preview_main.mp4`.
- Grund: Short mit mehreren Musik-Switches reicht nicht fuer finalen Musik-Review.
- Report: `reports/controlled_music_preview_run/step10a_find_proper_run_input/step10a_manifest.json`.
- Summary: `reports/controlled_music_preview_run/step10a_find_proper_run_input/step10a_summary.md`.
- Empfohlener Kandidat: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.

Top 3:
1. `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4` - 520.25s / 8.67min / 800312704 Bytes.
2. `exports/gaming_main/job_76374a6ddb88/job_76374a6ddb88_v1_final.mp4` - 486.569s / 8.11min / 727225858 Bytes.
3. `exports/gaming_main/job_d9811223d36c/job_d9811223d36c_v1_final.mp4` - 486.569s / 8.11min / 721638052 Bytes.

Grenzen:
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Step 10B richtigen Run auswaehlen nur nach Master-GO.

## Controlled Music Preview Run Schritt 9B-R Render New Clip With Allowed Output Root

Entscheidung: Master-GO fuer Step 9B-R. Kein Code-Fix, kein neuer Output-Root. Neuer bestaetigter Clip wird mit bestehendem erlaubtem Output-Root gerendert.

Beweis:
- Schritt 9B erster Versuch: NO-GO, weil `reports/controlled_music_preview_run/step9b_new_clip_after_input_fix_render` nicht erlaubt war.
- Genutzter Output-Root: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render`.
- Input: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`.
- Alter K7-Clip genutzt: nein.
- Output-MP4: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render/run_20260610_203039/controlled_music_preview_main.mp4`.
- Output-Groesse: `93774185` Bytes.
- Manifest: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render/run_20260610_203039/preview_render_manifest.json`.
- Step-9B-R-Report: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render/step9b_retry_manifest.json`.
- Content Type: `gaming_main`.
- Channel Type: `main`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- `vlog_background` genutzt: nein.
- `music_start_offset_sec=30.0`.
- `intro_trim_used=true`.
- `intro_boost_used=false`.
- Low-Speech Gains: `-27.0`, `-32.0`, `-25.0`.
- Manifest Status: `ok`.

Ergebnis:
- Controlled Music Preview Run Schritt 9B-R ausgefuehrt.
- Neuer Clip wurde lokal gerendert.
- Owner Review ist jetzt Pflicht.
- Naechster Schritt: Controlled Music Preview Run Schritt 10 Owner Review New Clip Final Tuning.

Grenzen:
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Runtime Learning.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Keine Produktionsdateien geaendert.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.

## Controlled Music Preview Run Schritt 9A Input-Allowlist-Fix

Entscheidung: Schritt 9 = NO-GO wegen hardcoded altem K7-Input. Code-GO nur fuer Step 9A Input-Allowlist-Fix, kein Render.

Beweis:
- Originalfehler: `hardcoded_old_k7_input_blocked_new_confirmed_clip`.
- Code-Commit: `72505ca` / `72505ca9af02cbbf51fe525ee8cf4d9844080ba3`.
- Geaendert: `scripts/controlled_music_preview_render.py`, `tests/test_controlled_music_preview_render.py`.
- Lokaler Report: `reports/controlled_music_preview_run/step9a_allowed_input_fix/step9a_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step9a_allowed_input_fix/step9a_summary.md`.

Ergebnis:
- Neuer bestaetigter Clip ist erlaubt:
  - `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
- Alter K7-Clip bleibt historisch erlaubt, aber es gibt keinen Auto-Fallback.
- Beliebige Inputs sind nicht erlaubt.
- Dry-Run mit neuem Clip ist gruen und nutzt exakt den neuen Clip.
- Naechster Schritt: Controlled Music Preview Schritt 9B Render neuer Clip nur nach Master-GO.

Grenzen:
- Kein Execute-Render.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 8B Neuer Clip festgeschrieben

Entscheidung: Master bestaetigt Kandidat 1 als neuen Clip fuer den naechsten Musik-Preview. Kein Render in Schritt 8B.

Beweis:
- Neuer Clip: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`.
- Groesse: `94364505` Bytes.
- LastWriteTime: `2026-06-05 06:07:32`.
- Lokaler Report: `reports/controlled_music_preview_run/step8b_new_clip_decision/step8b_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step8b_new_clip_decision/step8b_summary.md`.

Ergebnis:
- Alter K7-Clip wird fuer den naechsten Review nicht weiter benutzt.
- Neuer Clip ist festgeschrieben.
- `content_type=gaming_main`.
- `channel_type=main`.
- Musik-Kategorie fuer naechsten Render: `funny_gaming_background`.
- `vlog_background` bleibt verboten.
- Low-Speech Gains bleiben `-27.0`, `-32.0`, `-25.0`.
- Intro Offset bleibt `30.0`.
- Naechster Schritt: Controlled Music Preview Schritt 9 Render neuer Clip nur nach Master-GO.

Grenzen:
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 3 Content-Type-Fix

Entscheidung: Owner Review = FIX. Code-GO nur fuer Content-Type-Musik-Policy, kein neuer Render.

Beweis:
- Code-Commit: `a40f505` / `a40f505feeb04c9ce414b9136760ba6ae8037d64`.
- Policy-Datei: `core/music_content_type_policy.py`.
- Tests:
  - `tests/test_music_content_type_policy.py`
  - `tests/test_controlled_music_preview_render.py`
- Lokaler Report: `reports/controlled_music_preview_run/step3_owner_review_fix_content_policy/content_type_policy_fix_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step3_owner_review_fix_content_policy/content_type_policy_fix_summary.md`.

Ergebnis:
- `gaming_main` blockiert `vlog_background`.
- `vlog_main` blockiert `funny_gaming_background`, `fail`, `hype`.
- `uncut` blockiert Musik komplett.
- `gaming_main` Default Preview Kategorie: `funny_gaming_background`.
- `vlog_main` Default Preview Kategorie: `vlog_background`.
- K7/Rocket-League-Input ist im Preview-Script auf `content_type=gaming_main` begrenzt.
- Dry-Run zeigt `music_category=funny_gaming_background`.
- Naechster Schritt: Controlled Music Preview Schritt 4 Re-Render nur nach Master-GO.

Grenzen:
- Kein neuer Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 7A FFmpeg-Command-Fix

Entscheidung: Schritt 7 ist NO-GO wegen abgeschnittenem FFmpeg-Command. Code-GO nur fuer Step 7A FFmpeg-Command-Fix, kein Render.

Beweis:
- Originalfehler: `ffmpeg_command_truncated_after_stream_loop`.
- Fehlerhafter Command endete nach `-stream_loop -1`.
- FFmpeg stderr: `At least one output file must be specified`.
- Code-Commit: `6bfaff8` / `6bfaff8e8cb0aba3af954c178105d0396bc5c3c0`.
- Fix: `scripts/controlled_music_preview_render.py`.
- Tests: `tests/test_controlled_music_preview_render.py`.
- Lokaler Report: `reports/controlled_music_preview_run/step7a_ffmpeg_command_fix/ffmpeg_command_fix_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step7a_ffmpeg_command_fix/ffmpeg_command_fix_summary.md`.

Ergebnis:
- FFmpeg-Command-Builder baut wieder vollstaendigen Command.
- Musik-Input ist Pflicht.
- Output-Pfad ist Pflicht.
- `-filter_complex` ist Pflicht.
- mindestens zwei `-map` Eintraege sind Pflicht.
- mindestens zwei Inputs sind Pflicht.
- Command darf nicht nach `-stream_loop -1` enden.
- Dry-Run zeigt `music_start_offset_sec=30.0` und vollstaendigen Command.
- Naechster Schritt: Controlled Music Preview Schritt 7B Re-Render nur nach Master-GO.

Grenzen:
- Kein Execute-Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.

## Controlled Music Preview Run Schritt 7B Re-Render nach FFmpeg-Command-Fix

Entscheidung: Master-GO fuer genau einen kontrollierten Main-Account-Musik-Preview-Re-Render nach Step-7A-FFmpeg-Command-Fix.

Beweis:
- Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Output-MP4: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_153756/controlled_music_preview_main.mp4`.
- Output-Groesse: `107953864` Bytes.
- Manifest: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_153756/preview_render_manifest.json`.
- Summary: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_153756/preview_render_summary.md`.
- Step-7B-Report: `reports/controlled_music_preview_run/step7b_rerender_after_ffmpeg_fix/step7b_rerender_manifest.json`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- Channel Type: `main`.
- Content Type: `gaming_main`.
- Manifest Status: `ok`.

Ergebnis:
- Controlled Music Preview Run Schritt 7B ausgefuehrt.
- Genau ein neuer Preview-Re-Render wurde erzeugt.
- `vlog_background` wurde nicht genutzt.
- `music_start_offset_sec=30.0`.
- `intro_trim_used=true`.
- `intro_boost_used=false`.
- Low-Speech Gains bleiben `-22.0`, `-27.0`, `-20.0`.
- Owner Review ist jetzt Pflicht.
- Naechster Schritt: Ali Auge/Ohr Review mit GO / FIX / NO-GO.

Grenzen:
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Runtime Learning.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Keine Produktionsdateien geaendert.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.

## Controlled Music Preview Run Schritt 4 Gaming-Re-Render

Entscheidung: Master-GO fuer genau einen zweiten kontrollierten Main-Account-Musik-Preview-Re-Render mit `content_type=gaming_main`.

Beweis:
- Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Output-MP4: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/controlled_music_preview_main.mp4`.
- Output-Groesse: `107944673` Bytes.
- Manifest: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/preview_render_manifest.json`.
- Summary: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/preview_render_summary.md`.
- Step-4-Report: `reports/controlled_music_preview_run/step4_gaming_compatible_rerender/step4_rerender_manifest.json`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- Channel Type: `main`.
- Content Type: `gaming_main`.
- Manifest Status: `ok`.

Ergebnis:
- Controlled Music Preview Run Schritt 4 ausgefuehrt.
- Genau ein neuer Gaming-kompatibler Preview-Re-Render wurde erzeugt.
- `vlog_background` wurde nicht genutzt.
- Owner Review ist jetzt Pflicht.
- Naechster Schritt: Ali Auge/Ohr Review mit GO / FIX / NO-GO.

Grenzen:
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Runtime Learning.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Keine Produktionsdateien geaendert.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.

## Controlled Music Preview Run Schritt 6 Intro/Low-Speech-Tuning-Fix

Entscheidung: Owner Review Schritt 5 = GO mit Tuning-Fix. Code-GO nur fuer Intro-Offset-Policy und Low-Speech-Lautstaerke, kein neuer Render.

Beweis:
- Code-Commit: `79826e4` / `79826e410eee50349b224d9060efca97363a5cab`.
- Intro Policy: `core/music_intro_offset_policy.py`.
- Ducking Update: `core/music_ducking_plan.py`.
- Preview Script Dry-Run-Felder: `scripts/controlled_music_preview_render.py`.
- Tests:
  - `tests/test_music_intro_offset_policy.py`
  - `tests/test_p55_ducking_plan.py`
  - `tests/test_controlled_music_preview_render.py`
- Lokaler Report: `reports/controlled_music_preview_run/step6_owner_review_tuning_fix/tuning_fix_manifest.json`.
- Lokale Summary: `reports/controlled_music_preview_run/step6_owner_review_tuning_fix/tuning_fix_summary.md`.

Ergebnis:
- Quiet Intro Handling: `trim_start_offset`.
- Music Start Offset: `30.0`.
- Intro Boost erlaubt: nein.
- Low-Speech Base Gain: `-22.0`.
- Low-Speech Ducking Gain: `-27.0`.
- Low-Speech Max Gain: `-20.0`.
- Low-Speech / No-Speech Musik ca. 5 dB leiser geplant.
- Naechster Schritt: Controlled Music Preview Schritt 7 Re-Render nur nach Master-GO.

Grenzen:
- Kein neuer Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen gestartet.
- Kein Qwen-Autocut.
- Kein Runtime Learning gestartet.
- Musikdateien nicht committed.
- Reports nicht committed.
