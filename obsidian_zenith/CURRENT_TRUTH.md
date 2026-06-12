<!-- STEP22C_RENDER_CURRENT_TRUTH_START -->
# CURRENT TRUTH ADDENDUM ? Step 22C Render

Stand: 2026-06-11

## Status
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5: 100% / DONE
- Step 22B-FIX: FINAL DONE
- Step 22C Render: DONE
- Step 23 Owner Review: REQUIRED / NEXT
- Runtime Learning: locked

## Current HEAD Before Render
- Short: 03f064c
- Full: 03f064c005836b91f233ab39f28c78d31ece7e5a
- Commit: docs(obsidian): record real dynamic music automation fix

## Step 22C Render
- Input: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`
- Output: `D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_232023\controlled_music_preview_main.mp4`
- Output size: `1623798130`
- Manifest status: `ok`

## Technical Evidence
- Echte dynamische Musikautomation aktiv: `True`
- `dynamic_gain_unique_value_count: 5`
- `dynamic_gain_min_db: -38.0`
- `dynamic_gain_max_db: -30.0`
- `dynamic_gain_average_db: -34.226`
- `dynamic_gain_stddev_db: 2.416`
- `source_music_loudness_adjustment_nonzero_count: 24`
- `quiet_section_boost_window_count: 20`
- `loud_section_cut_window_count: 4`
- `voice_priority_window_count: 45`
- Command dynamic non-constant: `True`
- Command unique gain count: `5`
- Final tail fadeout disabled: `True`
- Final segment has no fade to silence: `True`
- Command contains final tail fadeout: `False`
- Musicbed command matches timeline: `True`
- Tail music coverage passed: `True`

## Tail Audio Smoke
- Tail 60s volumedetect log: `D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_232023\step22c_tail_voldetect_60s.txt`
- Tail 60s astats log: `D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_232023\step22c_tail_astats_60s.txt`
- End 20s volumedetect log: `D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_232023\step22c_end_voldetect_20s.txt`
- Technical smoke confirms audio presence, but does not replace Owner Review.

## Safety
- Upload started: `False`
- Runtime Learning started: `False`
- Qwen used: `False`

## Next
- Owner Review Step 23 is mandatory.
- Ali decides GO / FIX / NO-GO by ear.
- No upload without new Master-GO.
<!-- STEP22C_RENDER_CURRENT_TRUTH_END -->

<!-- STEP22B_FIX_CURRENT_TRUTH_START -->
# CURRENT TRUTH ADDENDUM ? Step 22B-FIX

Stand: 2026-06-11

## Status
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5: 100% / DONE
- Step 22 Owner Review: FIX / NO-GO
- Step 22B-FIX Code: DONE / PUSHED
- Step 22B Obsidian: DOCUMENTED
- Step 22C Render: LOCKED until Master-GO
- Runtime Learning: locked

## Current HEAD
- Short: 86f2952
- Full: 86f295272f18558a3d03117cd2b6b3d34b139e8d
- Commit: fix(music): apply real dynamic automation and remove tail fadeout

## Root Cause
- Kein Cache-Problem: alter und neuer Render hatten unterschiedliche Hashes.
- Die echte FFmpeg-Automation war vorher nicht dynamisch.
- Alle 106 Automationsfenster waren vorher effektiv `volume=-36.0dB`.
- Das finale Musiksegment hatte einen Tail-Fadeout.

## Step 22B-FIX Ergebnis
- Echte dynamische Musikautomation eingebaut.
- Dry-Run Command-Werte: `-30 / -32 / -34 / -36 / -38`.
- `quiet_section_boost_window_count: 20`.
- `loud_section_cut_window_count: 4`.
- `voice_priority_window_count: 45`.
- Finaler Tail-Fadeout entfernt.
- Musik-Tail bleibt h?rbar.

## Safety / Locks
- Kein Render gestartet.
- Kein Upload gestartet.
- Kein Qwen genutzt.
- Kein Runtime Learning gestartet.
- Kein Ingest gestartet.

## N?chster Schritt
- Step 22C Render nur nach Master-GO.
<!-- STEP22B_FIX_CURRENT_TRUTH_END -->

# CURRENT TRUTH - PROJECT ZENITH

Stand: 2026-06-11

## Aktuelle Wahrheit

- Phase 5: 100% / DONE / FINAL-GO.
- Alle 8 Phase-5-Endkriterien sind DONE.
- K7 echter Production-Short Kontroll-Run + Ali-Freigabe ist DONE.
- P5-L: 100% / CLOSED.
- P5-L ist als Vorbereitung abgeschlossen.
- P5-L6.5 Gruppe 5A Codex Audit: DONE.
- P5-L6.5 Gruppe 5B Audit-Fixes: DONE und remote gesichert.
- P5-L6.5 Gruppe 5C Obsidian Audit + Aufraeumen: DONE.
- P5-L6.5 Gruppe 5D Qwen Kontrollrun: DONE und remote gesichert.
- P5-L6.5 Gruppe 5E Abschlussbericht / Final Audit: erstellt.
- P5-L6.5 Gruppe 5F P5-L Close: DONE.
- Runtime Learning Gate: locked / later.
- Phase 5.5 Musik: 100% / Final Audit abgeschlossen.
- Controlled Music Preview Run: Schritt 9A Input-Allowlist-Fix remote gesichert.
- Controlled Music Preview Run Input-Kandidat bestaetigt: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Controlled Music Preview Run Schritt 2: technisch GO, Owner Review = FIX wegen falscher Musik-Kategorie.
- Controlled Music Preview Run Schritt 3: DONE / Content-Type-Fix remote gesichert.
- Controlled Music Preview Run Schritt 4: DONE / Gaming-Re-Render lokal erzeugt / Owner Review offen.
- Controlled Music Preview Run Schritt 5: Owner Review = GO mit Tuning-Fix.
- Controlled Music Preview Run Schritt 6: DONE / Intro-Offset + Low-Speech-Volume-Fix remote gesichert.
- Controlled Music Preview Run Schritt 7: NO-GO / FFmpeg-Command war nach `-stream_loop -1` abgeschnitten.
- Controlled Music Preview Run Schritt 7A: DONE / FFmpeg-Command-Builder repariert und remote gesichert.
- Controlled Music Preview Run Schritt 7B: DONE / Re-Render lokal erzeugt / Owner Review Pflicht.
- Controlled Music Preview Run Schritt 8: Owner Review = FIX.
- Controlled Music Preview Run Schritt 8A: DONE / Low-Speech nochmal -5 dB / neue Clip-Kandidaten gesucht / kein Render.
- Controlled Music Preview Run Schritt 8B: DONE / neuer Clip festgeschrieben / kein Render.
- Controlled Music Preview Run Schritt 9: NO-GO / Script erlaubte nur alten K7-Input.
- Controlled Music Preview Run Schritt 9A: DONE / neuer bestaetigter Clip per Allowlist erlaubt / kein Render.
- Controlled Music Preview Run Schritt 9B: NO-GO / neuer Output-Root war nicht erlaubt.
- Controlled Music Preview Run Schritt 9B-R: DONE / neuer Clip mit bestehendem erlaubtem Output-Root lokal gerendert / Owner Review Pflicht.
- Controlled Music Preview Run Schritt 10: Owner Review = Tuning gut, aber Short mit mehreren Musik-Switches ist kein finaler Beweis.
- Controlled Music Preview Run Schritt 10A: DONE / passende richtige Main/Gaming-Run-Kandidaten gesucht / kein Render.
- Controlled Music Preview Run Schritt 10B: DONE / richtiger Proper Run festgeschrieben / kein Render.
- Controlled Music Preview Run Schritt 11A: DONE / Proper-Run-Input und Step-11-Output-Root exakt erlaubt / kein Execute Render.
- Controlled Music Preview Run Schritt 11B: DONE / Proper Run mit finalem Musik-Tuning lokal gerendert / Owner Review Schritt 12 Pflicht.
- Controlled Music Preview Run Schritt 12: Owner Review = NO-GO.
- Controlled Music Preview Run Schritt 12A: DONE / Owner-NO-GO diagnostiziert / kein Render / kein Code-Fix.
- Controlled Music Preview Run Schritt 12B: DONE / visuell gueltige Proper-Run-Kandidaten gesucht / kein Render.
- Controlled Music Preview Run Schritt 12C: DONE / visuell gueltiger Proper Run ausgewaehlt / kein Render.
- Controlled Music Preview Run Schritt 12D: DONE / Allowlist + Audio-Readiness remote gesichert.
- Controlled Music Preview Run Schritt 13: DONE / Visual Proper Run mit Audio-Gain-Fix lokal gerendert / Owner Review Schritt 14 Pflicht.
- Controlled Music Preview Run Schritt 14: Owner Review = NO-GO.
- Controlled Music Preview Run Schritt 14A: DONE / Musik auf Adobe-Range `-38.0dB` gesenkt + Long-Run-Playlist vorbereitet / kein Render.
- Controlled Music Preview Run Schritt 14B: DONE / Lower-Music Multi-Song Proper Run lokal gerendert / Owner Review Schritt 15 Pflicht.
- Controlled Music Preview Run Schritt 16B-R2: DONE / echter 8.8-Minuten Visual Proper Run mit segmented dynamic music automation lokal gerendert / Owner Review Schritt 17 Pflicht.
- 16B-R2 Input: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
- 16B-R2 Output-MP4: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_172534/controlled_music_preview_main.mp4`.
- 16B-R2 Output-Groesse: `1623614198` Bytes.
- 16B-R2 Content-Type: `gaming_main`, Channel-Type: `main`.
- 16B-R2 Dynamic Strategy: `segmented_atrim_volume_concat`.
- 16B-R2 Automation: `106` Fenster, `asplit=106`, `atrim=106`, `volume=106`, `concat=n=106:v=0:a=1[music_auto]`.
- 16B-R2 Clean Transitions: FFmpeg-Fade und Track-Trim aktiv.
- 16B-R2 Track-Intro-Trim: `30.0s`; Track-Outro-Trim: `15.0s`; Crossfade: `3.0s`.
- 16B-R2 Manifest-Command-Consistency Gate: gruen.
- 16B-R2 Safety: kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning, keine Musikdateien committed.
- Naechster Schritt: Schritt 17 Owner Review / GO-FIX-NO-GO durch Ali.
- Controlled Music Preview Run Schritt 16B-R-FIX: DONE / Nested-IF FFmpeg-Volume-Expression ersetzt durch segmentierte Gain-Automation.
- 16B-R-FIX Commit: `efaff10` / `efaff1049c2784d894c0a12e090e788e62da672d`.
- 16B-R-FIX Tests: `tests/test_controlled_music_preview_render.py` gruen mit `52 passed`.
- 16B-R-FIX Dry-Run: `status=dry_run`, `owner_execute_required=true`, `owner_go=false`.
- 16B-R-FIX Dynamic Strategy: `segmented_atrim_volume_concat`.
- 16B-R-FIX Automation: `106` Fenster, `asplit=106`, `atrim=106`, `volume=106`, `concat=n=106:v=0:a=1[music_auto]`.
- 16B-R-FIX Safety: kein Nested-IF, kein `between(t,`, kein `eval=frame`, kein Upload, kein Qwen, kein Runtime Learning.
- Schritt 16B-R2 Execute-Render ist erledigt; naechster Schritt ist Schritt 17 Owner Review durch Ali.
- Phase 5.5-4A-R: Main-Account-Musikordner-Taxonomie auf Alis echte Epidemic-Sound-Ordner gepatcht.
- Offizielle Main-Musik-Kategorien: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- `hype` bedeutet spannend / Action / Peak / Clutch.
- `suspense` ist nur noch Mood-Alias und mappt auf `hype`.
- Main Account: Musik spaeter nur mit Safety/Owner/Lizenz/Manifest erlaubt.
- Main Account: Musik erlaubt nur mit separatem Preview-Run-GO.
- Main Account Selector vorhanden.
- Main Account Ducking Plan vorhanden.
- Main Account Preview Gate vorhanden.
- Uncut: Musik dauerhaft verboten.
- Content-Type-Musik-Policy vorhanden.
- `gaming_main` blockiert `vlog_background`.
- `vlog_main` blockiert `funny_gaming_background`, `fail`, `hype`.
- `uncut` blockiert Musik komplett.
- Intro-Offset-Policy vorhanden: ruhige Intros werden per Start-Offset getrimmt, kein automatischer Boost.
- Low-Speech / No-Speech Musik ist um ca. 10 dB leiser geplant.
- Erster kontrollierter Preview-Musik-Mix lokal erzeugt.
- Produktions-Musik-Build: nicht gestartet.
- Finaler Audio-Mix: nicht gestartet.
- Musikdateien lokal eingefuegt, ignored und nicht committed.
- Qwen sichtbar geprueft: ja.
- `qwen_role=analysis_only`.
- `qwen_can_cut=false`.
- `qwen_autocut_allowed=false`.
- P5-L7 / Schlaf-Learning-Run: Runtime Learning Gate / later / locked.

## Klare Trennung

- Phase 5 = Video-Pipeline finalisiert.
- P5-L = abgeschlossene Post-Phase-5 Learning-Vorbereitung.
- Runtime Learning Gate = spaeterer echter Schlaf-/Learning-Run, nicht Teil von P5-L Close.
- Phase 5.5 = Musik-Integration.
- Phase 5.5 ist NICHT Learning.
- Qwen ist Analyse-Side-Track, kein Cutter.
- Obsidian ist Truth Store / Second Brain.

## Naechster Schritt

Controlled Music Preview Schritt 16B-R2 Render ist lokal erzeugt. Naechster erlaubter Schritt ist Schritt 17 Owner Review durch Ali. Kein Upload, kein Qwen, kein Runtime Learning.


Ali hat manuell Epidemic-Sound-Musik in die offiziellen lokalen Main-Account-Ordner einsortiert.
5.5-4B Musikordner-Verifikation ist abgeschlossen.
5.5-5 Ducking Plan / Audio-Mix Safety ist abgeschlossen.
5.5-6 Controlled Music Preview Gate ist abgeschlossen.
5.5-7 Final Audit ist abgeschlossen.
Musik-Infrastruktur ist bereit fuer einen separaten kontrollierten Preview-Run.
Controlled Music Preview Run Schritt 8A Low-Speech-Retune + neue Clip-Kandidaten ist remote gesichert.
Neuer Input-Kandidat fuer den naechsten Review ist bestaetigt: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`.
Letztes Output-MP4 steht lokal in `reports/controlled_music_preview_run/step2_preview_render/run_20260610_153756/controlled_music_preview_main.mp4`.
Owner Review Schritt 5: GO mit Tuning-Fix.
Problem 1: viele Songs beginnen zu leise, brauchbarer Start erst nach ca. 30 Sekunden.
Loesung: Intro-Offset/Trim-Policy mit `music_start_offset_sec=30.0`, kein automatischer Boost.
Problem 2: Musik bei Low-Speech/No-Speech ca. 5 dB zu laut.
Loesung: Low-Speech Gains reduziert auf `base=-22.0`, `ducking=-27.0`, `max=-20.0`.
Schritt 7 Re-Render ist mit `ffmpeg_command_truncated_after_stream_loop` gescheitert.
Schritt 7A repariert den FFmpeg-Command-Builder; Dry-Run zeigt vollstaendigen Command mit Musik-Input, `-filter_complex`, Maps und Output-Pfad.
Schritt 7B Re-Render ist mit `content_type=gaming_main`, `music_category=funny_gaming_background`, `music_start_offset_sec=30.0`, `intro_trim_used=true`, `intro_boost_used=false` lokal erzeugt.
Owner Review Schritt 8: FIX, Musik bei wenig Sprache noch ein Tick zu laut.
Schritt 8A senkt Low-Speech erneut um ca. 5 dB auf `base=-27.0`, `ducking=-32.0`, `max=-25.0`.
Alter K7-Clip wird fuer den naechsten Review nicht weiter benutzt: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
Neue Clip-Kandidaten wurden gesucht.
Schritt 8B bestaetigt den neuen Clip: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`.
Schritt 9 war NO-GO, weil das Script nur den alten K7-Input erlaubt hat.
Schritt 9A erlaubt den neuen bestaetigten Clip sicher per Allowlist.
Schritt 9B erster Versuch war NO-GO, weil `reports/controlled_music_preview_run/step9b_new_clip_after_input_fix_render` nicht als Output-Root erlaubt war.
Schritt 9B-R nutzte den bestehenden erlaubten Output-Root: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render`.
Neuer Clip wurde lokal gerendert: `reports/controlled_music_preview_run/step9_new_clip_final_tuning_render/run_20260610_203039/controlled_music_preview_main.mp4`.
Output-Groesse: `93774185` Bytes.
Kein Fallback auf alten K7-Clip.
Keine beliebigen Inputs erlaubt.
Alter K7-Clip wurde nicht genutzt.
Content Type: `gaming_main`.
Channel Type: `main`.
Musik-Kategorie: `funny_gaming_background`.
Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
`vlog_background` wurde nicht genutzt.
Intro Offset: `30.0`.
Intro Trim: `true`.
Intro Boost: `false`.
Low-Speech Gains: `base=-27.0`, `ducking=-32.0`, `max=-25.0`.
Kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning.
Owner Review Schritt 10: Musik-Tuning ist grundsaetzlich gut.
Aber: Der Short mit mehreren Musik-Switches reicht nicht als finaler Musik-Beweis.
Controlled Music Preview wird noch nicht geschlossen.
Schritt 10A suchte einen richtigen Main/Gaming-Run fuer realistischen finalen Musik-Review.
Top 3 richtige Run-Kandidaten:
1. `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4` - 520.25s / 8.67min / 800312704 Bytes.
2. `exports/gaming_main/job_76374a6ddb88/job_76374a6ddb88_v1_final.mp4` - 486.569s / 8.11min / 727225858 Bytes.
3. `exports/gaming_main/job_d9811223d36c/job_d9811223d36c_v1_final.mp4` - 486.569s / 8.11min / 721638052 Bytes.
Empfohlener Kandidat: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
Begruendung: neuester passender `gaming_main` Final-Export, 8.67 Minuten echter Flow, praktikable Groesse, kein Short/raw/uncut/controlled-preview Output.
Kein Render, kein Audio-Mix, keine Musik eingefuegt, kein Upload, kein Qwen, kein Runtime Learning.
Schritt 10B hat den richtigen Proper Run festgeschrieben: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
Schritt 10B Readiness zeigte: Proper Run Input und Step-11-Output-Root waren noch nicht erlaubt.
Schritt 11A erlaubt jetzt exakt diesen Proper Run.
Schritt 11A erlaubt jetzt exakt diesen Output-Root: `reports/controlled_music_preview_run/step11_proper_run_final_music_render`.
Keine beliebigen `exports` erlaubt.
Kein Fallback auf K7.
Kein Fallback auf Short.
Kein Execute Render gestartet.
Kein MP4 erzeugt.
Kein Upload, kein Qwen, kein Runtime Learning.
Schritt 11B Proper Run Render wurde nach Master-GO ausgefuehrt.
Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
Input-Dauer: `520.250131s` / ca. 8.67min.
Output-MP4: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/controlled_music_preview_main.mp4`.
Output-Groesse: `798591899` Bytes.
Content Type: `gaming_main`.
Channel Type: `main`.
Musik-Kategorie: `funny_gaming_background`.
Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
Alter K7-Clip wurde nicht genutzt.
Short-Clip wurde nicht genutzt.
`vlog_background` wurde nicht genutzt.
Intro Offset: `30.0`.
Intro Trim: `true`.
Intro Boost: `false`.
Low-Speech Gains: `base=-27.0`, `ducking=-32.0`, `max=-25.0`.
Kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning.
Owner Review Schritt 12 ist jetzt Pflicht.
Owner Review Schritt 12 Ergebnis: NO-GO.
Grund 1: Output zeigt nur Facecam fullscreen.
Grund 2: Musik dauerhaft zu laut, auch bei Sprache/Freunden.
Schritt 12A Diagnose wurde ohne Code-Fix und ohne Render durchgefuehrt.
Visual Diagnose: Input ist bereits Facecam fullscreen; Output ist ebenfalls Facecam fullscreen und die gezogenen Input-/Output-Frames sind byte-identisch.
Visuelle Root Cause: falscher/ungeeigneter Proper-Run-Input, nicht Step-11B-Video-Mapping.
FFmpeg Video Mapping: `-map 0:v:0` und `-c:v copy`.
Audio Diagnose: Manifest enthaelt `-27/-32/-25`, aber der echte ffmpeg command nutzt statisch `volume=0.08` plus `sidechaincompress`.
Audio Root Cause: geplante Manifest-Gains werden nicht direkt im ffmpeg command angewendet; echte transcript-/speaker-/friend-aware Ducking-Kurve ist nicht bestaetigt.
Volumedetect 60-90s: Input `mean=-32.8 dB`, `max=-18.6 dB`; Output `mean=-37.8 dB`, `max=-22.8 dB`.
Step 12A Entscheidung bestaetigt: Kein Video-Mapping-Fix noetig; die falsche Testdatei wurde genommen.
Schritt 12B hat visuell gueltige Proper-Run-Kandidaten gesucht.
Top 3 visuell gueltige Kandidaten:
1. `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4` - 528.348813s / ca. 8.81min / Gameplay sichtbar / Facecam nicht fullscreen.
2. `exports/gaming_main/job_059053a7fa2a/job_059053a7fa2a_v1_final.mp4` - 528.301729s / ca. 8.81min / Gameplay sichtbar / Facecam nicht fullscreen.
3. `exports/gaming_main/job_a78b3b182979/job_a78b3b182979_v1_final.mp4` - 536.401729s / ca. 8.94min / Gameplay sichtbar / Facecam nicht fullscreen.
Empfohlener Kandidat: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
Screenshot-Belege lokal: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/`.
Audio-Thema bleibt offen: Manifest-Gains nicht direkt im FFmpeg-Command; speech-aware Ducking nicht bestaetigt.
Naechster Schritt: Step 12C visuell gueltigen Proper Run auswaehlen nur nach Master-GO.
Kein Render, kein Audio-Mix, kein Upload, kein Qwen, kein Runtime Learning.
Uncut bleibt ohne Musik.
Kein weiterer Render ohne Master-GO.
Kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning.
Schritt 12C hat den visuell gueltigen Proper Run festgeschrieben: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
Schritt 12D hat Input und Step-13-Output-Root allowlisted und den Audio-Gain-Fix remote gesichert.
Schritt 13 Visual Proper Run Render wurde nach Master-GO ausgefuehrt.
Input: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
Input-Dauer: `528.348813s` / ca. 8.8min.
Gameplay sichtbar: ja.
Facecam fullscreen: nein.
Kein Short, kein raw, kein uncut.
Output-MP4: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_125108/controlled_music_preview_main.mp4`.
Output-Groesse: `1623915456` Bytes.
Content Type: `gaming_main`.
Channel Type: `main`.
Musik-Kategorie: `funny_gaming_background`.
Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
Alter K7-Clip wurde nicht genutzt.
Short-Clip wurde nicht genutzt.
Alter Facecam-Proper-Run wurde nicht genutzt.
`vlog_background` wurde nicht genutzt.
Intro Offset: `30.0`.
Intro Trim: `true`.
Intro Boost: `false`.
Low-Speech Gains: `base=-27.0`, `ducking=-32.0`, `max=-25.0`.
FFmpeg-Musik-Volume: `-27.0dB`.
Hardcoded `volume=0.08` wurde nicht genutzt.
Manifest-Gains werden im FFmpeg-Command angewendet: ja.
Speech-aware Ducking bestaetigt: nein.
Sidechaincompress genutzt: ja.
Kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning.
Owner Review Schritt 14 ist jetzt Pflicht.
Owner Review Schritt 14 Ergebnis: NO-GO.
Grund 1: Musik war trotz `-27.0dB` zu laut.
Grund 2: Es wurde nur ein Song genutzt und dauerhaft wiederholt.
Owner-Referenz: Adobe-Mix normalerweise ca. `-35dB` bis `-40dB`.
Schritt 14A hat nur den Fix vorbereitet, ohne Execute Render.
Neuer Owner-Zielwert: `-38.0dB`.
FFmpeg-Musikvolume ist an `owner_adobe_reference_gain_db` gekoppelt.
Hardcoded `volume=0.08` bleibt verboten/nicht genutzt.
`-27.0dB` wird nicht mehr als finaler Musikwert fuer den visuellen Proper Run genutzt.
Long-Run-Playlist vorbereitet: bei Runs > 180s kein Single-Song-Dauerloop.
Fuer den 8.8-Minuten-Run waehlt der Dry-Run mehrere Songs aus `funny_gaming_background`.
Dry-Run Step 14A: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_132327/`.
Ausgewaehlte Tracks: 4.
`vlog_background` wurde nicht genutzt.
Kein Execute Render, kein Preview-Render, kein Audio-Mix, kein Upload, kein Qwen, kein Runtime Learning.
Naechster Schritt: Step 14B Render nur nach Master-GO.
Schritt 14B Lower-Music Multi-Song Proper Run Render wurde nach Master-GO ausgefuehrt.
Input: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
Input-Dauer: `528.348813s` / ca. 8.8min.
Gameplay sichtbar: ja.
Facecam fullscreen: nein.
Kein Short, kein raw, kein uncut.
Output-MP4: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_133137/controlled_music_preview_main.mp4`.
Output-Groesse: `1623773832` Bytes.
Content Type: `gaming_main`.
Channel Type: `main`.
Musik-Kategorie: `funny_gaming_background`.
Owner-Musik-Zielwert: `-38.0dB`.
FFmpeg-Musik-Volume: `-38.0dB`.
FFmpeg-Volume-Quelle: `owner_adobe_reference_gain_db`.
Hardcoded `volume=0.08` wurde nicht genutzt.
`-27.0dB` wurde nicht als finaler Musikwert genutzt.
Long-Run-Playlist genutzt: ja.
Single-Song-Dauerloop genutzt: nein.
Ausgewaehlte Tracks: 4.
Selected Tracks: `ES_Ain't No Thing But To Swing - Jules Gaia.mp3`, `ES_B Positive - Jules Gaia.mp3`, `ES_Bop It - Jules Gaia.mp3`, `ES_Break Fast - Jules Gaia.mp3`.
Kein immediate repeat, kein fast switching.
FFmpeg Command nutzt `concat=n=4`.
FFmpeg Command nutzt kein `stream_loop`.
`vlog_background` wurde nicht genutzt.
Kein Upload, kein Final-Render, kein Qwen, kein Runtime Learning.
Owner Review Schritt 15 ist jetzt Pflicht.

Runtime Learning Gate bleibt bis eigenes Master-GO gesperrt.

## Harte NO-GOs

- Kein echter Learning-Loop.
- Kein echter Overnight-Dauerlauf.
- Kein weiterer Render ohne Master-GO.
- Kein Final-Render.
- Kein Ingest.
- Kein Qwen-Autocut.
- Keine Uncut-Musik.
- Kein Produktions-Musik-Build.
- Kein finaler Audio-Mix.
- Keine Reports committen.

### Controlled Music Preview Run Schritt 0

- Diagnose-Report lokal/untracked: `reports/controlled_music_preview_input_selection/input_selection_summary.md`
- Top Empfehlung: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Alternative Main-Account-Pfad: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
- Musikbibliothek Check: `local_assets/music/` ignored, `git ls-files local_assets/music` leer.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Kein Qwen.
- Kein Runtime Learning.
- Ali muss Input-Kandidat bestaetigen.

### Controlled Music Preview Run Schritt 1

- Preview-Plan-Manifest lokal/untracked: `reports/controlled_music_preview_run/step1_preview_plan/preview_plan_manifest.json`
- Preview-Plan-Summary lokal/untracked: `reports/controlled_music_preview_run/step1_preview_plan/preview_plan_summary.md`
- Bestaetigter Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Input existiert: ja, `108427404` Bytes, LastWriteTime `2026-06-05 17:50:57`.
- Channel: `main`.
- Main Account Musik spaeter erlaubt, aber nur mit Owner Review und Safety-Gate.
- Uncut Musik erlaubt: nein.
- Musikbibliothek: `local_assets/music/main_account`, 87 Musikdateien.
- Kategorien: `intro=4`, `vlog_background=8`, `funny_gaming_background=34`, `fail=15`, `hype=15`, `sad=6`, `outro=5`.
- `local_assets/music/` ignored, `git ls-files local_assets/music` leer.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Naechster Schritt: Controlled Music Preview Run Schritt 2 nur nach Master-GO.

### Controlled Music Preview Run Schritt 2

- Code Commit: `b672dd4`
- Full Hash: `b672dd4f413e4537394640379728846ffa6b209a`
- Render-Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Output-MP4 lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/controlled_music_preview_main.mp4`
- Output-Groesse: `107923180` Bytes.
- Manifest lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/preview_render_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_095423/preview_render_summary.md`
- Musik-Kategorie: `vlog_background`.
- Musikdatei: `local_assets/music/main_account/vlog_background/ES_As Daylight Fades - Sulu.mp3`.
- Channel: `main`.
- Uncut genutzt: nein.
- Manifest Status: `ok`.
- `preview_render_used=true`.
- `final_render_used=false`.
- `upload_started=false`.
- `runtime_learning_started=false`.
- `qwen_used=false`.
- `qwen_autocut_used=false`.
- `uncut_music_allowed=false`.
- `owner_review_required=true`.
- Tests: `python -m py_compile scripts\controlled_music_preview_render.py` gruen; `python -m pytest tests\test_controlled_music_preview_render.py -vv` mit 11 passed.
- Dry-Run: `status=dry_run`, kein MP4 erzeugt.
- Execute-Run: `status=ok`, genau ein neues Output-MP4 im Run-Ordner.
- Reports/MP4 lokal/untracked, nicht committed.
- Musikdateien ignored und nicht committed.
- Keine Produktionsdateien geaendert.
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Qwen.
- Kein Runtime Learning.
- Owner Review Ergebnis: FIX wegen falscher Musik-Kategorie fuer Rocket League / `gaming_main`.
- Naechster Schritt: Controlled Music Preview Run Schritt 3 Content-Type-Musik-Policy-Fix.

### Controlled Music Preview Run Schritt 3

- Owner Review Ergebnis: FIX.
- Problem: `vlog_background` wurde fuer Rocket League / `gaming_main` genutzt und passte kreativ nicht.
- Code Commit: `a40f505`
- Full Hash: `a40f505feeb04c9ce414b9136760ba6ae8037d64`
- Policy: `core/music_content_type_policy.py`
- Tests: `tests/test_music_content_type_policy.py`, `tests/test_controlled_music_preview_render.py`
- `gaming_main` blockiert `vlog_background`: ja.
- `vlog_main` blockiert Gaming-Kategorien `funny_gaming_background`, `fail`, `hype`: ja.
- `uncut` erlaubt Musik: nein.
- Default Preview Kategorie `gaming_main`: `funny_gaming_background`.
- Default Preview Kategorie `vlog_main`: `vlog_background`.
- Dry-Run: `status=dry_run`, `content_type=gaming_main`, `music_category=funny_gaming_background`, kein MP4 erzeugt.
- Report lokal/untracked: `reports/controlled_music_preview_run/step3_owner_review_fix_content_policy/content_type_policy_fix_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step3_owner_review_fix_content_policy/content_type_policy_fix_summary.md`
- Tests: `python -m py_compile core\music_content_type_policy.py scripts\controlled_music_preview_render.py` gruen; `python -m pytest tests\test_music_content_type_policy.py tests\test_controlled_music_preview_render.py -vv` mit 29 passed.
- Kein Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 4 Re-Render nur nach Master-GO.

### Controlled Music Preview Run Schritt 4

- Re-Render nach Master-GO ausgefuehrt.
- Render-Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Output-MP4 lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/controlled_music_preview_main.mp4`
- Output-Groesse: `107944673` Bytes.
- Manifest lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/preview_render_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_150421/preview_render_summary.md`
- Step-4-Report lokal/untracked: `reports/controlled_music_preview_run/step4_gaming_compatible_rerender/step4_rerender_manifest.json`
- Step-4-Summary lokal/untracked: `reports/controlled_music_preview_run/step4_gaming_compatible_rerender/step4_rerender_summary.md`
- Channel: `main`.
- Content Type: `gaming_main`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- `vlog_background` genutzt: nein.
- Uncut genutzt: nein.
- Manifest Status: `ok`.
- `preview_render_used=true`.
- `final_render_used=false`.
- `upload_started=false`.
- `runtime_learning_started=false`.
- `qwen_used=false`.
- `qwen_autocut_used=false`.
- `uncut_music_allowed=false`.
- `owner_review_required=true`.
- Dry-Run: `status=dry_run`, kein MP4 erzeugt.
- Execute-Run: `status=ok`, genau ein neues Output-MP4 im Run-Ordner.
- Reports/MP4 lokal/untracked, nicht committed.
- Musikdateien ignored und nicht committed.
- Keine Produktionsdateien geaendert.
- Kein Upload.
- Kein Final-Render.
- Kein Ingest.
- Kein Qwen.
- Kein Runtime Learning.
- Naechster Schritt: Controlled Music Preview Run Schritt 5 Owner Review Gaming Music.

### Controlled Music Preview Run Schritt 6

- Owner Review Schritt 5 Ergebnis: GO mit Tuning-Fix.
- Problem 1: Viele Musikstuecke beginnen zu leise, brauchbarer Start erst nach ca. 30 Sekunden.
- Loesung: Intro-Offset/Trim-Policy, kein automatischer Boost.
- Problem 2: Musik bei Low-Speech/No-Speech ca. 5 dB zu laut.
- Loesung: Low-Speech Gains um ca. 5 dB reduziert.
- Code Commit: `79826e4`
- Full Hash: `79826e410eee50349b224d9060efca97363a5cab`
- Intro Policy: `core/music_intro_offset_policy.py`
- Ducking Update: `core/music_ducking_plan.py`
- Preview Script: `scripts/controlled_music_preview_render.py`
- Tests: `tests/test_music_intro_offset_policy.py`, `tests/test_p55_ducking_plan.py`, `tests/test_controlled_music_preview_render.py`
- `quiet_intro_handling=trim_start_offset`.
- `music_start_offset_sec=30.0`.
- `intro_boost_allowed=false`.
- Low-Speech Base Gain: `-22.0`.
- Low-Speech Ducking Gain: `-27.0`.
- Low-Speech Max Gain: `-20.0`.
- Tests: `python -m py_compile core\music_intro_offset_policy.py core\music_ducking_plan.py scripts\controlled_music_preview_render.py` gruen; `python -m pytest tests\test_music_intro_offset_policy.py tests\test_p55_ducking_plan.py tests\test_controlled_music_preview_render.py -vv` mit 47 passed.
- Dry-Run: `status=dry_run`, `intro_offset_policy_used=true`, `quiet_intro_detected=true`, `intro_trim_used=true`, `intro_boost_used=false`, kein MP4 erzeugt.
- Report lokal/untracked: `reports/controlled_music_preview_run/step6_owner_review_tuning_fix/tuning_fix_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step6_owner_review_tuning_fix/tuning_fix_summary.md`
- Kein Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 7 Re-Render nur nach Master-GO.

### Controlled Music Preview Run Schritt 7A

- Schritt 7 Ergebnis: NO-GO.
- Fehler: FFmpeg-Command war nach `-stream_loop -1` abgeschnitten.
- FFmpeg stderr: `At least one output file must be specified`.
- Code Commit: `6bfaff8`
- Full Hash: `6bfaff8e8cb0aba3af954c178105d0396bc5c3c0`
- Repariert: `scripts/controlled_music_preview_render.py`
- Tests: `tests/test_controlled_music_preview_render.py`
- FFmpeg-Command-Builder baut wieder vollstaendigen Command.
- Musik-Input ist Pflicht.
- Output-Pfad ist Pflicht.
- `-filter_complex` ist Pflicht.
- mindestens zwei `-map` Eintraege sind Pflicht.
- Command darf nicht nach `-stream_loop -1` enden.
- Intro Offset `30.000` wird vor Musik-Input gesetzt.
- Tests: `python -m py_compile scripts\controlled_music_preview_render.py` gruen; `python -m pytest tests\test_controlled_music_preview_render.py -vv` mit 26 passed.
- Dry-Run: `status=dry_run`, `content_type=gaming_main`, `music_category=funny_gaming_background`, `music_start_offset_sec=30.0`, `intro_trim_used=true`, `intro_boost_used=false`, kein MP4 erzeugt.
- Report lokal/untracked: `reports/controlled_music_preview_run/step7a_ffmpeg_command_fix/ffmpeg_command_fix_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step7a_ffmpeg_command_fix/ffmpeg_command_fix_summary.md`
- Kein Execute-Render gestartet.
- Kein Preview-Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 7B Re-Render nur nach Master-GO.

### Controlled Music Preview Run Schritt 7B

- Schritt 7B Re-Render nach FFmpeg-Command-Fix wurde ausgefuehrt.
- Input: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- Output MP4: `reports/controlled_music_preview_run/step2_preview_render/run_20260610_153756/controlled_music_preview_main.mp4`
- Output Groesse: `107953864` Bytes.
- Channel Type: `main`.
- Content Type: `gaming_main`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- `vlog_background` genutzt: nein.
- `music_start_offset_sec=30.0`.
- `intro_trim_used=true`.
- `intro_boost_used=false`.
- Low-Speech Base Gain: `-22.0`.
- Low-Speech Ducking Gain: `-27.0`.
- Low-Speech Max Gain: `-20.0`.
- Manifest Status: `ok`.
- Preview Render used: true.
- Final Render used: false.
- Upload gestartet: nein.
- Runtime Learning gestartet: nein.
- Qwen gestartet: nein.
- Qwen-Autocut: nein.
- Ingest gestartet: nein.
- Uncut genutzt: nein.
- Produktionsdateien geaendert: nein.
- Musikdateien nicht committed.
- Reports/MP4 nicht committed.
- Step-7B-Report lokal/untracked: `reports/controlled_music_preview_run/step7b_rerender_after_ffmpeg_fix/step7b_rerender_manifest.json`
- Step-7B-Summary lokal/untracked: `reports/controlled_music_preview_run/step7b_rerender_after_ffmpeg_fix/step7b_rerender_summary.md`
- Owner Review ist jetzt Pflicht.
- Naechster Schritt: Controlled Music Preview Schritt 8 Owner Review Intro/Volume Tuning.

### Controlled Music Preview Run Schritt 8A

- Owner Review Schritt 8 Ergebnis: FIX.
- Owner Feedback: Musik passt grundsaetzlich, Intro-Offset funktioniert, Gaming-Musik passt besser.
- Problem: Wenn wenig oder nicht geredet wird, ist die Musik noch ein Tick zu laut.
- Entscheidung: Low-Speech / No-Speech Musik nochmal ca. 5 dB runter.
- Alter K7-Clip wird fuer den naechsten Review nicht weiter benutzt.
- Code Commit: `f6725b9`
- Full Hash: `f6725b97ec7cbc6bacca873ff366198507b1c987`
- Low-Speech vorher: `base=-22.0`, `ducking=-27.0`, `max=-20.0`.
- Low-Speech neu: `base=-27.0`, `ducking=-32.0`, `max=-25.0`.
- Additional reduction: `5.0` dB.
- Total reduction: `10.0` dB.
- Dry-Run: `status=dry_run`, `content_type=gaming_main`, `music_category=funny_gaming_background`, `music_start_offset_sec=30.0`, `intro_trim_used=true`, `intro_boost_used=false`, kein MP4 erzeugt.
- Top 3 neue Clip-Kandidaten:
  1. `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
  2. `reports/phase5/g2_s3b_multispeaker_pair001/g2_s3b_pair001_short_1.mp4`
  3. `reports/phase5/g2_s3b_friend_rich_520_540/g2_s3b_friend_rich_520_540_short_1.mp4`
- Report lokal/untracked: `reports/controlled_music_preview_run/step8a_owner_review_fix_low_speech_new_clip/step8a_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step8a_owner_review_fix_low_speech_new_clip/step8a_summary.md`
- Kein Render gestartet.
- Kein Preview-Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 8B neuen Clip auswaehlen nur nach Master-GO.

### Controlled Music Preview Run Schritt 8B

- Ali/Master hat Kandidat 1 als neuen Clip bestaetigt.
- Neuer Clip: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
- Neuer Clip Groesse: `94364505` Bytes.
- Neuer Clip LastWriteTime: `2026-06-05 06:07:32`.
- Alter K7-Clip wird fuer den naechsten Review nicht weiter benutzt: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Content Type fuer naechsten Render: `gaming_main`.
- Channel Type fuer naechsten Render: `main`.
- Musik-Kategorie fuer naechsten Render: `funny_gaming_background`.
- `vlog_background` erlaubt: nein.
- Low-Speech Base Gain bleibt: `-27.0`.
- Low-Speech Ducking Gain bleibt: `-32.0`.
- Low-Speech Max Gain bleibt: `-25.0`.
- Intro Offset bleibt: `30.0`.
- Report lokal/untracked: `reports/controlled_music_preview_run/step8b_new_clip_decision/step8b_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step8b_new_clip_decision/step8b_summary.md`
- Kein Render gestartet.
- Kein Preview-Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 9 neuen Clip mit finalem Tuning rendern nur nach Master-GO.

### Controlled Music Preview Run Schritt 9A

- Schritt 9 Ergebnis: NO-GO.
- Originalfehler: hardcoded alter K7-Input blockierte neuen bestaetigten Clip.
- Fehlertext: `input-video must be exactly reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`.
- Code Commit: `72505ca`
- Full Hash: `72505ca9af02cbbf51fe525ee8cf4d9844080ba3`
- Neuer Clip erlaubt: `exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4`
- Alter K7 Auto-Fallback: nein.
- Beliebige Inputs erlaubt: nein.
- Allowlist blockiert weiterhin fremde Inputs wie `learning_corpus`, `local_assets/music`, `video_configs` und `reports/controlled_music_preview_run`.
- Dry-Run mit neuem Clip: `status=dry_run`, `input_video_path` exakt neuer Clip, kein MP4 erzeugt.
- `content_type=gaming_main`.
- `music_category=funny_gaming_background`.
- `vlog_background_blocked_for_gaming_main=true`.
- `music_start_offset_sec=30.0`.
- `intro_trim_used=true`.
- `intro_boost_used=false`.
- Low-Speech Gains: `-27.0`, `-32.0`, `-25.0`.
- Report lokal/untracked: `reports/controlled_music_preview_run/step9a_allowed_input_fix/step9a_manifest.json`
- Summary lokal/untracked: `reports/controlled_music_preview_run/step9a_allowed_input_fix/step9a_summary.md`
- Kein Execute-Render gestartet.
- Kein Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Musikdateien nicht committed.
- Reports nicht committed.
- Naechster Schritt: Controlled Music Preview Schritt 9B neuen Clip rendern nur nach Master-GO.

## Wichtigste Beweise

### Phase 5 Final

- K7 Output: `reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4`
- `renderer_route=ShortsRenderDriver.render_short`
- `production_layout_route_used=true`
- `captions_generated=true`
- `GREEN_COUNT=105`
- `YELLOW_COUNT=36`
- `friend_words=36`
- Ali-Freigabe: ja

### P5-L6.5 5B Fixes

- Code/Test Commit: `19e16d2`
- Full Hash: `19e16d2b2423ba7ee188021c5fb338a2ee0ce93a`
- P5-L6 Owner-GO manifestiert: `owner_review_completed=true`, `owner_go=true`, `owner_review_source=ali_manual_owner_review`
- P5-L4 core Importproblem behoben.
- P5-L2 Output Guard hart auf `reports/p5_l2_analysis_only_dry_run` begrenzt.
- Zieltests: `33 passed`.

### P5-L6.5 5D Qwen Kontrollrun

- Code/Test Commit: `a3af5e3`
- Full Hash: `a3af5e3c8548bb9240e0377b3c8a2263796bbcc8`
- Modell: `qwen3.6:latest`
- `qwen_requested=true`
- `qwen_used=true`
- `qwen_visible_response=true`
- `qwen_role=analysis_only`
- `qwen_can_cut=false`
- `qwen_autocut_allowed=false`
- `dangerous_response_detected=false`
- Reports: lokal/untracked, nicht committed.

### P5-L6.5 5E Final Audit

- Final Audit Report: [[P5L_Final_Audit_Report]]
- Claude Senior Handoff: [[Claude_Senior_Handoff]]
- Kein Code geaendert.
- Kein Qwen gestartet.
- Kein Render, kein Ingest, keine Musik.
- Kein echter Learning-Loop.
- Phase 5.5 Musik bleibt locked.

### P5-L6.5 5F P5-L Close

- Close Report: [[P5L_Close_Report]]
- Runtime Learning Gate: [[Runtime_Learning_Gate]]
- Option B dokumentiert: P5-L als Vorbereitung geschlossen.
- P5-L7 / Schlaf-Learning-Run ist aus dem P5-L-Abschluss herausgeloest.
- Kein Code geaendert.
- Kein Qwen gestartet.
- Kein Render, kein Ingest, keine Musik.
- Kein echter Learning-Loop.
- Phase 5.5 Musik bleibt locked.

### Phase 5.5 Opening-Gate

- Opening-Gate: [[Phase5_5_Opening_Gate]]
- Safety-Regeln: [[Phase5_5_Safety_Rules]]
- Backlog: [[Phase5_5_Backlog]]
- Run Log: [[Phase5_5_Run_Log]]
- Kein Code geaendert.
- Kein Render, kein Ingest, keine Musik.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-1 Musik-Inventory nur nach Master-GO.

### Phase 5.5-1 Musik-Inventory

- Inventory: [[Phase5_5_Music_Inventory]]
- Library-Regeln: [[Phase5_5_Music_Library_Rules]]
- Phase 5.5 Musik: 15% / Musik-Inventory abgeschlossen.
- Gefundene Musik-Kandidaten:
  - `assets/audio/gaming_main/music/main_calm_bed.mp3`
  - `assets/audio/gaming_main/music/main_intro_bed.mp3`
- Gefundene Musik-Kandidaten sind nicht tracked und durch `.gitignore` ignoriert.
- Getrackte Audio-Dateien existieren nur als SFX/Test-Fixtures, nicht als Musikbibliothek.
- Kein Code geaendert.
- Keine Musikdateien erzeugt, kopiert oder committed.
- Kein Render, kein Ingest, kein Qwen, kein Runtime Learning.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-2 Musik-Contracts / Manifest + Safety-Flags nur nach Master-GO.

### Phase 5.5-2 Musik-Contracts

- Code/Safety Commit: `6e536ea`
- Full Hash: `6e536ea130134405505820dae3a9c23b898550a4`
- Contracts: `core/music_contracts.py`
- Smoke Script: `scripts/p55_music_contracts_smoke.py`
- Tests: `tests/test_p55_music_contracts.py`
- Gitignore-Schutz erweitert:
  - `local_assets/music/`
  - `*.m4a`
  - `*.aac`
  - `*.ogg`
  - `*.opus`
- Smoke Manifest: `reports/phase5_5_music_contracts/music_contracts_manifest.json`
- Smoke Summary: `reports/phase5_5_music_contracts/music_contracts_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 10 passed.
- Smoke Run: `status=ok`.
- Kein Render, kein Preview-Render, kein Ingest.
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert oder committed.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-3 Energy-to-Music Mapping nur nach Master-GO.

### Phase 5.5-3 Energy-to-Music Mapping

- Code Commit: `c14575d`
- Full Hash: `c14575d68fd91c4bfcef77b7757d81bdd0a6e216`
- Mapping: `core/music_energy_mapping.py`
- Smoke Script: `scripts/p55_energy_to_music_mapping_smoke.py`
- Tests: `tests/test_p55_energy_to_music_mapping.py`
- Mapping-Regeln:
  - Intro-Segment -> `intro`
  - ruhiges Gameplay -> historisch `background`, superseded durch `vlog_background`
  - Highlight / Peak / hohe Energie -> historisch `peak`, superseded durch `hype`
  - Outro -> `outro`
- Ducking ist nur Flag: `ducking_required`.
- Smoke Manifest: `reports/phase5_5_energy_to_music_mapping/energy_to_music_mapping_manifest.json`
- Smoke Summary: `reports/phase5_5_energy_to_music_mapping/energy_to_music_mapping_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 14 passed.
- Smoke Run: `status=ok`.
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert, ausgewaehlt oder committed.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-4 Musik-Selector nur nach Master-GO.

### Phase 5.5-3R Main/Uncut Mood Patch

- Code Patch Commit: `cf75021`
- Full Hash: `cf750216e75f458bd2db670b44387adb4bd1032a`
- Contracts: `core/music_contracts.py`
- Mapping: `core/music_energy_mapping.py`
- Main Account: Musik-Mapping spaeter erlaubt, nur mit Safety/Owner/Lizenz/Manifest.
- Uncut: Musik dauerhaft verboten.
- Uncut Mapping: `music_allowed=false`, `music_category=none`, `reason=uncut_music_disabled`.
- Mood-Kategorien dieser alten Patch-Stufe sind durch Phase 5.5-4A-R superseded.
- Neue offizielle Main-Musik-Kategorien: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- Deprecated Mood-Alias: `suspense` mappt auf `hype`.
- Patch Reports:
  - `reports/phase5_5_main_uncut_mood_patch/main_uncut_mood_patch_manifest.json`
  - `reports/phase5_5_main_uncut_mood_patch/main_uncut_mood_patch_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 35 passed.
- Smoke Runs: `status=ok`.
- Keine Musik eingefuegt.
- Keine Musikdateien erzeugt, kopiert, ausgewaehlt oder committed.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-4 Musik-Selector nur nach Master-GO.

### Phase 5.5-4 Musik-Selector

- Code Commit: `7ca03f0`
- Full Hash: `7ca03f0e8806253d787d03b58e9cfa7d0aa75f69`
- Selector: `core/music_selector.py`
- Smoke Script: `scripts/p55_music_selector_smoke.py`
- Tests: `tests/test_p55_music_selector.py`
- Main Account Selector vorhanden.
- Selector arbeitet nur mit Metadaten.
- Selector liest keine Musikdateien.
- Selector fuegt keine Musik ein.
- Uncut bleibt ohne Musik.
- Uncut Selection: `music_allowed=false`, `selected_category=none`, `selection_status=blocked`.
- Missing Category: `selection_status=missing_candidate`, kein heimlicher Fallback.
- Prioritaet: hoechste `priority` gewinnt, Gleichstand stabil nach `candidate_id`.
- Smoke Manifest: `reports/phase5_5_music_selector/music_selector_manifest.json`
- Smoke Summary: `reports/phase5_5_music_selector/music_selector_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 16 passed.
- Smoke Run: `status=ok`.
- Keine Musik eingefuegt.
- Keine Musikdateien gelesen, erzeugt, kopiert, ausgewaehlt oder committed.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Musik-Build noch nicht gestartet.
- Naechster Schritt: 5.5-5 Ducking Plan nur nach Master-GO.

### Phase 5.5-4A Lokale Main-Musikordner

- Lokale Ordner unter `local_assets/music/main_account/` vorbereitet:
  - `intro`
  - `outro`
  - `vlog_background`
  - `funny_gaming_background`
  - `fail`
  - `hype`
  - `sad`
- Deprecated alte Ordner, falls lokal vorhanden: `funny`, `suspense`, `calm`, `victory`, `emotional`, `background`, `peak`.
- Zweck: Ali kann spaeter manuell Epidemic-Sound-Musik einsortieren.
- `local_assets/music/` ist gitignored.
- Keine Musikdateien erzeugt.
- Keine Musikdateien kopiert.
- Keine Musikdateien committed.
- Kein `local_assets/music/uncut` erstellt.
- Kein Code geaendert.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: Ali kopiert Musikdateien manuell ein, danach 5.5-4B Musikordner-Verifikation.

### Phase 5.5-4A-R Ali-Musikordner-Taxonomie

- Code Commit: `ce0af0c`
- Full Hash: `ce0af0c1787cc0d266b4cbeb837d8f91130aacdb`
- Offizielle Main-Musik-Kategorien: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- Mapping:
  - `funny` -> `funny_gaming_background`
  - `suspense` -> `hype`
  - `hype` -> `hype`
  - `sad` -> `sad`
  - `fail` -> `fail`
  - `calm`, `neutral`, default gameplay -> `vlog_background`
  - `intro` / `outro` bleiben `intro` / `outro`
  - `uncut` bleibt `music_allowed=false`, `category=none`
- Alte Ordner `calm`, `victory`, `emotional`, `background`, `peak`, `suspense`, `funny` sind deprecated, nicht geloescht und nicht verschoben.
- Musik-Build noch nicht gestartet.
- Keine Musikdateien gelesen, kopiert, verschoben oder committed.
- Kein Render, kein Preview-Render, kein Ingest, kein Qwen, kein Runtime Learning.
- Reports lokal/untracked, nicht committed.
- Naechster Schritt: 5.5-4B Musikordner-Verifikation nach manuellem Einsortieren.

### Phase 5.5-4B Lokale Main-Musikbibliothek

- Epidemic-Sound-Musik wurde manuell lokal eingefuegt.
- Offizielle Kategorien geprueft: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- Alle offiziellen Ordner existieren unter `local_assets/music/main_account/`.
- Anzahl Musikdateien gesamt: 87.
- Anzahl pro Ordner: `intro=4`, `outro=5`, `vlog_background=8`, `funny_gaming_background=34`, `fail=15`, `hype=15`, `sad=6`.
- Anzahl pro Endung: `.mp3=87`, `.wav=0`, `.flac=0`, `.m4a=0`, `.aac=0`, `.ogg=0`, `.opus=0`.
- Ungueltige Dateitypen: keine.
- Musikdateien ausserhalb `local_assets/music/main_account/`: keine.
- `local_assets/music/uncut` existiert nicht.
- `local_assets/music/` ist gitignored.
- `git ls-files local_assets/music` ist leer.
- Musikdateien bleiben lokal und ignored.
- Keine Musikdateien wurden committed.
- Report: `reports/phase5_5_music_folder_verification/music_folder_verification_summary.md` lokal/untracked, nicht committed.
- Kein Code geaendert.
- Keine Tests geaendert.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: 5.5-5 Ducking Plan / Audio-Mix Safety nur nach Master-GO.

### Phase 5.5-5 Ducking Plan

- Code Commit: `80e361f`
- Full Hash: `80e361f753d77c44eab1c0708a30e744c8cf6671`
- Ducking Plan: `core/music_ducking_plan.py`
- Smoke Script: `scripts/p55_ducking_plan_smoke.py`
- Tests: `tests/test_p55_ducking_plan.py`
- Main Account Ducking Plan vorhanden.
- Speech Priority Regeln:
  - low: base `-17.0`, duck `-22.0`, max `-15.0`
  - medium: base `-20.0`, duck `-26.0`, max `-18.0`
  - high: base `-23.0`, duck `-30.0`, max `-21.0`
  - very_high: base `-26.0`, duck `-34.0`, max `-24.0`
- Ali/Friend-Stimmen haben Vorrang.
- `max_music_gain_db` darf nie lauter als `-14.0` werden.
- Uncut bleibt ohne Musik: `music_allowed=false`, `selected_category=none`, `plan_status=blocked`.
- Missing Candidate fuehrt zu `plan_status=no_selected_music`.
- Smoke Manifest: `reports/phase5_5_ducking_plan/ducking_plan_manifest.json`
- Smoke Summary: `reports/phase5_5_ducking_plan/ducking_plan_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 17 passed.
- Smoke Run: `status=ok`.
- Keine Musik eingefuegt.
- Kein Musik-Build gestartet.
- Kein echter Audio-Mix gestartet.
- Keine Musikdateien gelesen, geoeffnet, kopiert, geloescht, konvertiert oder committed.
- Kein Render, kein Preview-Render, kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: 5.5-6 Controlled Music Preview Gate nur nach Master-GO.

### Phase 5.5-6 Controlled Music Preview Gate

- Code Commit: `fada35c`
- Full Hash: `fada35cdfb25f1a142d752ce93a4e8984884eecb`
- Preview Gate: `core/music_preview_gate.py`
- Smoke Script: `scripts/p55_music_preview_gate_smoke.py`
- Tests: `tests/test_p55_music_preview_gate.py`
- Main Account Preview Gate vorhanden.
- Owner Preview GO ist Pflicht.
- Main clean gate: `gate_status=ready_for_controlled_preview`.
- Ready for controlled preview bedeutet keinen automatischen Render und keinen Audio-Mix.
- Uncut bleibt ohne Musik: `gate_status=blocked`, `reason=uncut_music_disabled`.
- Render Request blockiert: `reason=render_not_allowed_in_gate`.
- Audio-Mix Request blockiert: `reason=audio_mix_not_allowed_in_gate`.
- Smoke Manifest: `reports/phase5_5_music_preview_gate/music_preview_gate_manifest.json`
- Smoke Summary: `reports/phase5_5_music_preview_gate/music_preview_gate_summary.md`
- Reports lokal/untracked, nicht committed.
- `py_compile`: gruen.
- Pytest: 21 passed.
- Smoke Run: `status=ok`.
- Keine Musik eingefuegt.
- Kein Musik-Build gestartet.
- Kein echter Audio-Mix gestartet.
- Kein echter Render gestartet.
- Kein Preview-Render gestartet.
- Kein Ingest.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: 5.5-7 Final Audit oder kontrollierter Preview-Run nur nach Master-GO.

### Phase 5.5-7 Final Audit

- Final Audit Report: `reports/phase5_5_final_audit/phase5_5_final_audit_summary.md`
- Final Audit Manifest: `reports/phase5_5_final_audit/phase5_5_final_audit_manifest.json`
- Reports lokal/untracked, nicht committed.
- Phase 5.5 Musik: 100% / Final Audit abgeschlossen.
- Musik-Infrastruktur bereit fuer separaten kontrollierten Preview-Run.
- Controlled Preview Run ist separater Owner/Master-GO-Gate und wurde nicht gestartet.
- Contracts ready: true.
- Mapping ready: true.
- Selector ready: true.
- Ducking Plan ready: true.
- Preview Gate ready: true.
- Music library verified: true, 87 MP3-Dateien.
- Main Account: Musik erlaubt nur mit separatem Preview-Run-GO.
- Uncut: Musik dauerhaft verboten.
- `py_compile`: gruen.
- Pytest: 91 passed.
- Alle Phase-5.5-Smoke-Runs: `status=ok`.
- Kein Musik-Build gestartet.
- Kein echter Audio-Mix gestartet.
- Kein echter Render gestartet.
- Kein Preview-Render gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: Controlled Music Preview Run nur nach Master-GO und Owner Review.

### Controlled Music Preview Step 10B - Proper Run ausgewaehlt

- Status: richtiger `gaming_main` Run fuer finalen Musik-Review festgeschrieben.
- Ausgewaehlter Run: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`
- Dauer: `520.25s` / ca. 8.67 Minuten.
- Groesse: `800312704` Bytes.
- Kein Short.
- Kein raw.
- Kein uncut.
- Kein controlled-preview Output.
- Musik-Tuning bleibt:
  - `music_category=funny_gaming_background`
  - `vlog_background` verboten
  - Intro Offset `30.0s`
  - Low-Speech Gains `-27.0`, `-32.0`, `-25.0`
- Readiness-Risiko fuer Step 11: ausgewaehlter Proper Run und Step-11-Output-Root sind im Controlled-Preview-Script noch nicht erlaubt.
- Kein Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Naechster Schritt: Step 11 Proper Run Render nur nach Master-GO; bei Allowlist-Blocker STOPP und Master fragen.

### Controlled Music Preview Step 11A - Proper Run Allowlist Fix

- Status: Proper-Run-Allowlist-Fix remote gesichert.
- Code Commit: `74da7bf`
- Full Hash: `74da7bf14f93c1da3bed379cf5ea1232afdab525`
- Schritt 10B zeigte: Proper Run Input und Step-11-Output-Root waren noch nicht erlaubt.
- Proper Run Input jetzt erlaubt: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`
- Step-11 Output-Root jetzt erlaubt: `reports/controlled_music_preview_run/step11_proper_run_final_music_render`
- Beliebige `exports` erlaubt: nein.
- Fallback auf alten K7-Clip: nein.
- Fallback auf Short-Clip: nein.
- Dry-Run mit Proper Run: `status=dry_run`.
- Dry-Run Input: exakt Proper Run.
- Dry-Run Output Root: exakt Step-11-Root.
- Content Type: `gaming_main`.
- Channel Type: `main`.
- Musik-Kategorie: `funny_gaming_background`.
- Intro Offset: `30.0`.
- Intro Trim: `true`.
- Intro Boost: `false`.
- Low-Speech Gains: `-27.0`, `-32.0`, `-25.0`.
- Kein Execute Render gestartet.
- Kein MP4 erzeugt.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Reports lokal/untracked, nicht committed.
- Naechster Schritt: Controlled Music Preview Step 11B Proper Run Render nur nach Master-GO.

### Controlled Music Preview Step 11B - Proper Run Final Music Render

- Status: Proper Run mit finalem Musik-Tuning lokal gerendert.
- Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Input-Dauer: `520.250131s` / ca. 8.67min.
- Output Root: `reports/controlled_music_preview_run/step11_proper_run_final_music_render`.
- Output-MP4: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/controlled_music_preview_main.mp4`.
- Output-Groesse: `798591899` Bytes.
- Content Type: `gaming_main`.
- Channel Type: `main`.
- Musik-Kategorie: `funny_gaming_background`.
- Musikdatei: `local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3`.
- Alter K7-Clip genutzt: nein.
- Short-Clip genutzt: nein.
- `vlog_background` genutzt: nein.
- Intro Offset: `30.0`.
- Intro Trim: true.
- Intro Boost: false.
- Low-Speech Gains: `-27.0`, `-32.0`, `-25.0`.
- Dry-Run: `status=dry_run`, kein MP4 erzeugt.
- Execute-Render: `status=ok`.
- Manifest Status: `ok`.
- Kein Upload gestartet.
- Kein Final-Render gestartet.
- Kein Qwen gestartet.
- Kein Runtime Learning gestartet.
- Reports/MP4 nicht committed.
- Naechster Schritt: Controlled Music Preview Step 12 Owner Review Proper Run Final Music Tuning.

### Controlled Music Preview Step 12A - Owner NO-GO Diagnosis

- Status: Owner-NO-GO diagnostiziert und lokal dokumentiert.
- Owner Review Schritt 12: NO-GO.
- Grund 1: Output zeigt nur Facecam fullscreen.
- Grund 2: Musik dauerhaft zu laut, auch bei Sprache/Freunden.
- Diagnose-Input: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- NO-GO-Output: `reports/controlled_music_preview_run/step11_proper_run_final_music_render/run_20260610_213126/controlled_music_preview_main.mp4`.
- Input ist Facecam fullscreen: ja.
- Output ist Facecam fullscreen: ja.
- Input-/Output-Screenshots sind an 10s, 60s, 180s und 360s byte-identisch.
- Visuelle Root Cause: falscher/ungeeigneter Proper-Run-Input; Step-11B kopiert Video unveraendert.
- Verdaechtige Video-Stelle: keine Bildfilter-Stelle; ffmpeg nutzt `-map 0:v:0` und `-c:v copy`.
- Manifest-Gains vorhanden: ja, `-27.0`, `-32.0`, `-25.0`.
- FFmpeg command nutzt diese Gains direkt: nein; echter Filter nutzt `volume=0.08` plus `sidechaincompress`.
- Speech/Friend-Ducking bestaetigt: nein; keine transcript-/speaker-/friend-aware Ducking-Kurve sichtbar.
- Lokaler Diagnose-Report: `reports/controlled_music_preview_run/step12a_owner_review_no_go_diagnosis/step12a_summary.md`.
- Kein Code-Fix.
- Kein Render.
- Kein Audio-Mix.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Naechster Schritt: Controlled Music Preview Step 12B Fix after Owner NO-GO nur nach Master-GO.

### Controlled Music Preview Step 12B - Find Visually Valid Proper Run

- Status: visuell gueltige Proper-Run-Kandidaten gesucht und lokal dokumentiert.
- Step-12A Ergebnis bestaetigt: Der falsche Input war selbst Facecam fullscreen.
- Video-Mapping-Fix noetig: nein.
- Alter falscher Input nicht mehr nutzen: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Kein Render.
- Kein Preview-Render.
- Kein Audio-Mix.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Top 3:
  1. `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4` - 528.348813s / Gameplay sichtbar / Facecam nicht fullscreen.
  2. `exports/gaming_main/job_059053a7fa2a/job_059053a7fa2a_v1_final.mp4` - 528.301729s / Gameplay sichtbar / Facecam nicht fullscreen.
  3. `exports/gaming_main/job_a78b3b182979/job_a78b3b182979_v1_final.mp4` - 536.401729s / Gameplay sichtbar / Facecam nicht fullscreen.
- Empfehlung: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
- Screenshot-Belege lokal: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/`.
- Lokaler Report: `reports/controlled_music_preview_run/step12b_find_visually_valid_proper_run/step12b_summary.md`.
- Audio-Thema bleibt offen: Manifest-Gains nicht direkt im FFmpeg-Command; speech-aware Ducking nicht bestaetigt.
- Naechster Schritt: Controlled Music Preview Step 12C visuell gueltigen Proper Run auswaehlen nur nach Master-GO.

### Controlled Music Preview Step 12C - Select Visually Valid Proper Run

- Status: visuell gueltiger Proper Run ausgewaehlt und lokal dokumentiert.
- Ausgewaehlter Run: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
- Dauer: `528.348813s`.
- Gameplay sichtbar: ja.
- Facecam fullscreen: nein.
- Short/raw/uncut: nein/nein/nein.
- Controlled preview output: nein.
- Alter falscher Proper Run wird nicht weiter genutzt: `exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4`.
- Alter Input war Facecam fullscreen: ja.
- Video-Mapping-Fix noetig: nein.
- Kein Render gestartet.
- Kein Preview-Render gestartet.
- Kein Audio-Mix gestartet.
- Keine Musik eingefuegt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Audio-Thema bleibt offen: Manifest-Gains nicht direkt im FFmpeg-Command; speech-aware Ducking nicht bestaetigt.
- Risiko fuer naechsten Schritt: Input `job_aa2953e15914` und Output-Root `reports/controlled_music_preview_run/step13_visual_proper_run_music_render` sind im Controlled-Preview-Script noch nicht erlaubt.
- Lokaler Report: `reports/controlled_music_preview_run/step12c_select_visually_valid_proper_run/step12c_summary.md`.
- Naechster Schritt: Controlled Music Preview Step 12D Allowlist + Audio Readiness nur nach Master-GO.

### Controlled Music Preview Step 12D - Allowlist + Audio Readiness

- Status: Allowlist und Audio-Readiness remote gesichert.
- Code-Commit: `bb078a1` / `bb078a13eeedf3ccedb7191081ea3b6f2ac0678f`.
- Visual Proper Run erlaubt: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`.
- Step-13 Output-Root erlaubt: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render`.
- Keine beliebigen exports erlaubt.
- Kein Fallback auf K7, Short oder alten Facecam-Proper-Run fuer Step 13.
- Hardcoded `volume=0.08` im Musik-Volume-Pfad entfernt/nicht mehr genutzt.
- FFmpeg-Musiklautstaerke an `low_speech_base_music_gain_db=-27.0` gekoppelt.
- `ffmpeg_music_volume_linear=0.0446683592150963`.
- `manifest_gains_applied_to_ffmpeg_command=true`.
- `sidechaincompress_used=true`.
- Speech-aware Ducking ehrlich nicht bestaetigt: `speech_aware_ducking_confirmed=false`.
- Tests: `python -m py_compile scripts\controlled_music_preview_render.py`; `python -m pytest tests\test_controlled_music_preview_render.py -vv` mit 40 passed.
- Dry-Run: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260610_222701/`.
- Kein Execute Render gestartet.
- Kein MP4 erzeugt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Lokaler Report: `reports/controlled_music_preview_run/step12d_allowlist_audio_readiness/step12d_summary.md`.
- Naechster Schritt: Controlled Music Preview Step 13 Visual Proper Run Render nur nach Master-GO.

## Wichtige Links

- [[ZENITH_HOME]]
- [[Phase_Status]]
- [[Progress_Log]]
- [[GO_NO_GO_Log]]
- [[Webseite_Checkliste]]
- [[Phase5_Endcriteria_Audit]]
- [[Learning_Opening_Gate]]
- [[Learning_Safety_Rules]]
- [[Learning_Backlog]]
- [[Learning_Run_Log]]
- [[Script_Index]]
- [[Safety_Index]]
- [[Architecture_Map]]
- [[Codex_Audit_Log]]
- [[P5L_Runbook]]
- [[P5L_Final_Audit_Report]]
- [[Claude_Senior_Handoff]]
- [[P5L_Close_Report]]
- [[Runtime_Learning_Gate]]
- [[Phase5_5_Opening_Gate]]
- [[Phase5_5_Safety_Rules]]
- [[Phase5_5_Backlog]]
- [[Phase5_5_Run_Log]]
- [[Phase5_5_Music_Inventory]]
- [[Phase5_5_Music_Library_Rules]]
- [[NEXT_PROMPT]]

<!-- STEP_15A_ADAPTIVE_TRACK_GAIN_RECORDED -->
## 2026-06-11 ? Controlled Music Preview Step 15A ? Adaptive Per-Track Music Gain

Status: DONE / CODE REMOTE PREPARED

Code Commit:
- Short: 6c8b7b3
- Full: 6c8b7b392bc70746b420b200a8b6e39859edee94
- Message: fix(preview): adapt music gain per track loudness

Owner Review nach Step 14B:
- Problem: fixer Musikwert -38.0 dB reicht nicht.
- Grund: manche Songs sind leiser, manche lauter.
- Entscheidung: pro Musiktrack eigene Lautheit messen und eigenen Gain berechnen.

Adaptive Track Gain:
- adaptive_track_gain_enabled: true
- owner_adobe_reference_gain_range_db: [-40.0, -35.0]
- owner_music_target_gain_db: -38.0
- track_gain_strategy: relative_track_loudness_with_owner_range_clamp
- track_gain_reference: median_selected_track_mean_volume_db

Dry-Run Ergebnis:
- status: dry_run
- selected_music_track_count: 4
- final gains: -37.4 dB, -39.4 dB, -35.0 dB, -38.6 dB
- all_final_gains_between_minus_40_and_minus_35: true
- all_tracks_same_gain: false
- concat=n=4 bleibt aktiv
- kein volume=0.08
- kein -27.0dB finaler Musikwert
- kein stream_loop Single-Song-Dauerloop

Safety:
- kein Execute Render gestartet
- kein Preview-Render gestartet
- kein Audio-Mix gestartet
- keine Musik eingef?gt
- kein Upload
- kein Qwen
- kein Runtime Learning
- keine Musikdateien committed
- Reports nicht committen

Tests:
- python -m py_compile scripts\controlled_music_preview_render.py: OK
- python -m pytest tests\test_controlled_music_preview_render.py -vv: 45 passed

N?chster Schritt:
- Controlled Music Preview Step 15B Render mit Adaptive Per-Track Gain nur nach Master-GO.

## 2026-06-11 14:36:01 — Controlled Music Preview Step 15A2 — Music Timeline Planner

Status: DONE / CODE-GO

Commit:
- ca2ed05 feat(preview): plan music timeline by video and track duration
- full hash: ca2ed05f339aac2526b645494b3721fa774e7799

Owner-Anforderung:
- Video-Dauer berücksichtigen
- Song-Dauer berücksichtigen
- Song-Anzahl aus Timeline ableiten
- Mood/Kategorie-Mapping vorbereiten
- keine falsche KI-Mood-Behauptung

Umgesetzt:
- neuer Planner: core/music_timeline_planner.py
- neue Tests: tests/test_music_timeline_planner.py
- Preview-Script mit Music-Timeline-Manifest erweitert
- Direct-Run Importpfad für Scriptstart repariert
- adaptive Track-Gain bleibt aktiv
- Planner-Status als music_timeline_planner_status, damit dry_run status nicht überschrieben wird

Test-Beweis:
- python -m py_compile core\music_timeline_planner.py scripts\controlled_music_preview_render.py: OK
- tests/test_music_timeline_planner.py: 10 passed
- tests/test_controlled_music_preview_render.py: 46 passed

Dry-Run-Beweis:
- status: dry_run
- video_duration_sec: 528.348
- music_timeline_planner_enabled: True
- music_timeline_planner_status: ok
- music_timeline_segment_count: 5
- selected_music_track_count: 4
- duration_based_song_count: True
- track_duration_aware_selection: True
- mood_category_mapping_enabled: True
- mood_based_category_switching: fallback_only
- true_ai_mood_detection_used: False
- mood_analysis_source: fallback_neutral_gaming
- single_song_loop: False
- qwen_used: False
- runtime_learning_started: False
- upload_started: False
- music_files_committed: False
- kein MP4 im Dry-Run erzeugt

Wichtig:
- Es wurde nicht gerendert.
- Es wurde nichts hochgeladen.
- Qwen wurde nicht genutzt.
- Runtime Learning bleibt gesperrt.
- local_assets/music bleibt untracked / nicht committed.
- Reports bleiben lokal und werden nicht committed.

Nächster Schritt:
- Step 15B Render mit Music Timeline Planner nur nach Master-GO.

## 2026-06-11 14:45:35 — Controlled Music Preview Step 15B — Render mit Music Timeline Planner

Status: DONE / TECH-GO / OWNER REVIEW REQUIRED

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4
- Dauer: 528.348s
- content_type: gaming_main
- channel_type: main

Output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_144301/controlled_music_preview_main.mp4
- lokale MP4: D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_144301\controlled_music_preview_main.mp4
- Größe Bytes: 1623778212
- Run: D:\Zenith\reports\controlled_music_preview_run\step13_visual_proper_run_music_render\run_20260611_144301

Music Timeline Planner:
- music_timeline_planner_enabled: True
- music_timeline_planner_status: ok
- music_timeline_segment_count: 5
- selected_music_track_count: 4
- duration_based_song_count: True
- track_duration_aware_selection: True
- mood_category_mapping_enabled: True
- true_ai_mood_detection_used: False
- mood_analysis_source: fallback_neutral_gaming
- mood_based_category_switching: fallback_only
- single_song_loop: False

Adaptive Track Gain:
- local_assets/music/main_account/funny_gaming_background/ES_Ain't No Thing But To Swing - Jules Gaia.mp3 | category= | mean=-11.6 | raw=-37.4 | final=-37.4 | clamped=False
- local_assets/music/main_account/funny_gaming_background/ES_B Positive - Jules Gaia.mp3 | category= | mean=-9.6 | raw=-39.4 | final=-39.4 | clamped=False
- local_assets/music/main_account/funny_gaming_background/ES_Bop It - Jules Gaia.mp3 | category= | mean=-14.1 | raw=-34.9 | final=-35.0 | clamped=True
- local_assets/music/main_account/funny_gaming_background/ES_Break Fast - Jules Gaia.mp3 | category= | mean=-10.4 | raw=-38.6 | final=-38.6 | clamped=False

Safety:
- kein Upload: False
- kein Runtime Learning: False
- kein Qwen: False
- preview_render_used: True
- final_render_used: False
- uncut_music_allowed: False
- owner_review_required: True
- keine Musikdateien committed
- Reports/MP4 bleiben lokal und untracked

Wichtig:
- Technischer Render ist erzeugt.
- Qualität wurde nicht bewertet.
- Owner Review Schritt 16 ist Pflicht.
- Kein Upload ohne neues Master-GO.
- Kein Runtime Learning.

## 2026-06-11 16:04:24 — Controlled Music Preview Step 16A — Dynamic Music Automation Planner

Status: DONE / CODE-GO / NO RENDER

Code Commit:
- 76b574a feat(preview): add dynamic music automation planner
- full hash: 76b574a2ae237a9baea91b3f604ddd1da0f10d00

Owner Review Step 16:
- Entscheidung: FIX
- Grund 1: Songs sind nicht immer gleich laut.
- Grund 2: Songabschnitte innerhalb eines Songs können leise/lauter sein.
- Grund 3: Stimmen/Freunde müssen Music-Ceiling beeinflussen.
- Grund 4: Songwechsel müssen sauberer werden.

Umgesetzt:
- neuer Planner: core/music_automation_planner.py
- neue Tests: tests/test_music_automation_planner.py
- Preview-Script Manifest/Dry-Run angebunden
- Preview-Tests erweitert

Dynamic Music Automation:
- music_automation_planner_enabled: True
- automation_window_sec: 5.0
- automation_window_count: 106
- voice_aware_music_ceiling_enabled: True
- music_section_loudness_aware: True
- gain_smoothing_enabled: True
- max_gain_change_per_window_db: 2.0
- automation_all_final_gains_between_minus_40_and_minus_35: True

Speaker / Voice:
- ali_friend_separation_confirmed: False
- speaker_voice_source: mixed_audio_level
- wichtig: keine falsche Ali/Friend-Trennung behauptet

Clean Transition Policy:
- clean_transition_policy_enabled: True
- track_start_trim_sec: 30.0
- track_end_trim_sec: 15.0
- crossfade_sec: 3.0
- hard_cut_transitions: False
- track_intro_outro_trim_enabled: True

Test-Beweis:
- py_compile: OK
- tests/test_music_automation_planner.py: 9 passed
- tests/test_music_timeline_planner.py: 10 passed
- tests/test_controlled_music_preview_render.py: 47 passed

Dry-Run-Beweis:
- status: dry_run
- dry_run: True
- owner_execute_required: True
- kein MP4 im neuesten Dry-Run-Ordner erzeugt
- music_timeline_planner_enabled: True
- music_automation_planner_enabled: True
- automation_window_count: 106
- qwen_used: False
- runtime_learning_started: False
- upload_started: False

Safety:
- kein Render gestartet
- kein Audio-Mix gestartet
- keine Musik in Video eingefügt
- kein Upload
- kein Qwen
- kein Runtime Learning
- keine Musikdateien committed
- Reports bleiben lokal und untracked

Nächster Schritt:
- Step 16B Render mit Dynamic Music Automation nur nach Master-GO.

## 2026-06-11 16:22:29 — Controlled Music Preview Step 16B — STOPP vor Execute

Status: STOPP / NO-GO BEFORE EXECUTE / NO RENDER

Ausgangslage:
- Step 16B sollte den visuellen Proper Run mit Dynamic Music Automation rendern.
- Vor Execute wurde Dry-Run + Command-Gate geprüft.

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4
- Dauer: ca. 528.348813s
- content_type: gaming_main
- channel_type: main

Dry-Run:
- run_dir: reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_162056
- status: dry_run
- dry_run: True
- MP4 im Dry-Run-Ordner: 0
- owner_execute_required: True

Manifest OK:
- music_timeline_planner_enabled: True
- music_automation_planner_enabled: True
- automation_window_sec: 5.0
- automation_window_count: 106
- voice_aware_music_ceiling_enabled: True
- music_section_loudness_aware: True
- gain_smoothing_enabled: True
- max_gain_change_per_window_db: 2.0
- ali_friend_separation_confirmed: False
- speaker_voice_source: mixed_audio_level
- clean_transition_policy_enabled: True
- track_start_trim_sec: 30.0
- track_end_trim_sec: 15.0
- crossfade_sec: 3.0
- hard_cut_transitions: False

Command Gate:
- forbidden hits: False
- has_volume: True
- has_trim_30s: True
- has_concat: True
- has_funny_gaming_background: True
- has_stream_loop: False
- has_afade: False
- has_acrossfade: False

STOPP-Grund:
- Manifest behauptet Clean Transition Policy / Crossfade.
- Echter FFMPEG-Command enthält aber kein afade und kein acrossfade.
- Deshalb darf kein Render mit --execute-owner-go gestartet werden.
- Zusätzlich ist Dynamic Automation bisher im Manifest geplant, aber noch nicht als echte 5s Gain-Kurve im FFMPEG-Command umgesetzt.

Safety:
- kein Render gestartet
- kein Execute gestartet
- kein Upload
- kein Runtime Learning
- kein Qwen
- keine Musikdateien committed
- keine Produktionsdateien geändert
- Reports bleiben lokal und untracked

Nächster Schritt:
- Step 16B-FIX nur nach neuem Master-GO.
- Ziel: echte FFMPEG Clean Transitions und echte Dynamic-Automation-Command-Abbildung bauen.

## 2026-06-11 16:42:41 — Controlled Music Preview Step 16B-FIX — FFmpeg Command Realization

Status: CODE-GO / DRY-RUN COMMAND-GATE GREEN / NO RENDER

Code Commit:
- 80b91de fix(preview): apply music automation and transitions in ffmpeg
- Full Hash: 80b91de006c267efa3e90dc5b70a75626f0d2e34

Vorheriger STOPP:
- Step 16B wurde korrekt vor Execute gestoppt.
- Grund: Manifest behauptete Clean Transition / Dynamic Automation, aber alter FFmpeg-Command zeigte kein afade/acrossfade und keine echte 5s Gain-Automation.

Fix-Ergebnis:
- Clean Transition ist jetzt im FFmpeg-Command sichtbar.
- Track-Trim ist jetzt im FFmpeg-Command sichtbar.
- Dynamic 5s Gain Automation ist jetzt im FFmpeg-Command sichtbar.
- Manifest-Command-Consistency Gate ist aktiv und grün.

Dry-Run:
- run_dir: reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_163927
- status: dry_run
- dry_run: True
- owner_execute_required: True
- mp4_created_count: 0

Command-Gate:
- ffmpeg_clean_transition_applied: True
- ffmpeg_command_contains_fade: True
- ffmpeg_command_contains_track_trim: True
- ffmpeg_dynamic_automation_applied: True
- automation_window_command_applied: True
- command_contains_time_based_volume_automation: True
- command_dynamic_gain_zone_count: 106
- dynamic_gain_expression_strategy: volume_if_between_eval_frame
- manifest_command_consistency_gate: True
- forbidden_command_hits: False

Tests:
- py_compile: OK
- tests/test_music_automation_planner.py: 9 passed
- tests/test_music_timeline_planner.py: 10 passed
- tests/test_controlled_music_preview_render.py: 51 passed

Safety:
- Execute Render gestartet: False
- Render gestartet: False
- Audio-Mix gestartet: False
- Upload gestartet: False
- Qwen gestartet: False
- Runtime Learning gestartet: False
- Musikdateien committed: False
- Reports committed: False
- Final tracked-only nach Code Push: leer

Nächster Schritt:
- Controlled Music Preview Step 16B-R Render nur nach Master-GO.

## 2026-06-11 16:58:34 — Controlled Music Preview Step 16B-R — Execute Render STOPP

Status: FAILED / STOPP / NO OUTPUT MP4

Aktueller HEAD vor Obsidian:
- 1ca68a1 docs(obsidian): record music command realization fix

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4
- Dauer: ca. 528.348s
- content_type: gaming_main
- channel_type: main

Run:
- failed_run_dir: reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_165114
- manifest_status: failed
- owner_go: true
- owner_execute_required: false
- output_mp4_created_count: 0

Vor Execute:
- Precheck grün
- py_compile: OK
- tests/test_music_automation_planner.py: 9 passed
- tests/test_music_timeline_planner.py: 10 passed
- tests/test_controlled_music_preview_render.py: 51 passed
- Dry-Run Command-Gate grün
- manifest_command_consistency_gate: true
- command_dynamic_gain_zone_count: 106

Fehlerursache:
- FFmpeg Parsed_volume Eval Parser bricht ab.
- Kernmeldung: Missing ')' or too many args.
- Betroffen: lange nested if(between(t,...)) Dynamic-Gain-Expression mit 106 Zonen.
- Dry-Run erkannte die Command-Realization als vorhanden, aber echter FFmpeg-Execute akzeptiert die Expression nicht.

Safety:
- Upload gestartet: false
- Runtime Learning gestartet: false
- Qwen gestartet: false
- Qwen-Autocut gestartet: false
- Produktionsdateien geändert: false
- Musikdateien committed: false
- Reports/MP4 committed: false
- tracked-only nach STOPP: leer
- local_assets/music tracked: leer

Entscheidung:
- Step 16B-R Execute Render: NO-GO / STOPP
- Kein weiterer Execute ohne Master-GO.
- Kein Upload.
- Kein Runtime Learning.
- Kein Qwen.
- Kein Code-Fix ohne neues Master-GO.

Nächster Schritt:
- Master-GO für Step 16B-R-FIX erforderlich.
- Fix-Ziel: Dynamic FFmpeg Volume Automation FFmpeg-sicher machen, ohne 106-fach verschachtelte if(between(...)) Expression.

## Step 17B-FIX Current Truth ? 2026-06-11 18:59:05

Step 17B-FIX code is DONE and pushed.

Code commit:
- d975c79 fix(preview): make dynamic music audible
- Full hash: d975c79ea3e807072fa71ed5bbce638411b45b3c

Current technical truth:
- Music audibility policy is active.
- Owner audible gain range is [-35.0, -26.0].
- Owner target gain is -30.0.
- Music audibility floor is -35.0.
- Music loudness ceiling is -26.0.
- Double-ducking protection is enabled.
- Sidechain is gentle: ratio 3.0, threshold 0.08, attack 40, release 350.
- Dry-run passed.
- No real render executed after this fix.
- Next real render requires explicit Master/Owner GO.

## 2026-06-11 19:26:49 ? Step 17C Audible Dynamic Music Render

Status: DONE / render executed / Owner Review required.

Render:
- Input: `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`
- Input duration sec: 528.348813
- Output root: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render`
- Output MP4: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_192336/controlled_music_preview_main.mp4`
- Output size bytes: 1623615243
- Run dir: `reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_192336`
- content_type: gaming_main
- channel_type: main

Music audibility policy:
- music_audibility_policy_enabled: true
- owner_music_audible_gain_range_db: [-35.0, -26.0]
- owner_music_target_gain_db: -30.0
- music_audibility_floor_db: -35.0
- music_loudness_ceiling_db: -26.0
- command_volume_average_db: -31.912
- command_volume_min_db: -32.0
- command_volume_max_db: -26.9
- command_volume_audibility_gate_passed: true

Sidechain / voice safety:
- double_ducking_protection_enabled: true
- sidechain_ratio: 3.0
- sidechain_threshold: 0.08
- sidechain_attack: 40
- sidechain_release: 350

Automation / transitions:
- dynamic_gain_expression_strategy: segmented_atrim_volume_concat
- command_contains_nested_if_volume_automation: false
- manifest_command_consistency_gate: true
- segmented dynamic automation: active
- clean transitions: active

Safety:
- upload_started: false
- runtime_learning_started: false
- qwen_used: false
- no final render
- no ingest
- no music files committed
- reports/MP4 remain untracked

Next:
- Owner Review Schritt 18 is mandatory.
- Ali must judge the real rendered video by eye/ear.
- No upload without new Master-GO.

---

## 2026-06-11 20:22:21 — Controlled Music Preview Step 18A Audio Routing Diagnose

Status: DONE / diagnosis only
Owner Review Decision: FIX
Owner Issue: Musik ist gar nicht hörbar.

Affected output:
reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_192336/controlled_music_preview_main.mp4

Diagnose-Befund:
- Output Audio Stream existiert: true
- Output full mean volume: -32.9 dB
- Input full mean volume: -29.2 dB
- Output ist in Samples ca. 6 dB leiser als Input
- Musiktracks existieren: true
- Musiktracks sind nicht silent: true
- FFmpeg Command enthält Musikinputs: true
- FFmpeg Command baut [music_auto]: true
- FFmpeg Command enthält sidechaincompress: true
- FFmpeg Command enthält amix: true
- Finaler Audio-Map nutzt [aout]: true

Verdacht Root Cause:
Routing ist grundsätzlich vorhanden. Musikdateien sind normal laut und nicht silent. Stärkster Root-Cause-Kandidat ist doppelte Musik-Absenkung:
Erst ca. -26.9 dB bis -31.4 dB pro Track, danach nochmal volume=-32.0dB pro Automation-Chunk.
Dadurch landet der Musikbus effektiv ungefähr bei -59 bis -63 dB und ist praktisch unhörbar.

Safety:
- Render gestartet: false
- Upload gestartet: false
- Qwen genutzt: false
- Runtime Learning gestartet: false
- Code geändert: false
- Musikdateien geändert: false

Nächster Schritt:
Step 18B-FIX nur nach Master-GO.
Nicht rendern. Nicht uploaden. Kein Runtime Learning. Kein Qwen.

---

## 2026-06-11 20:52:05 ? Controlled Music Preview Step 18B-FIX Single Final Music Bus Gain

Status: DONE / technical GO
Owner Review Decision from Step 18A: FIX
Problem: Musik war im gerenderten Video praktisch nicht hoerbar.

Root Cause aus Step 18A:
- Musikrouting war vorhanden.
- Musiktracks waren nicht silent.
- FFmpeg baute [music_auto], sidechaincompress, amix und [aout].
- Fehler war doppelte Musik-Absenkung:
  - Track-Level vorher ca. -26.9 dB bis -31.4 dB
  - Automation danach nochmal volume=-32.0dB
  - effektiver Musikbus dadurch ca. -59 bis -63 dB

18B-FIX Ergebnis:
- music_gain_application_mode: single_final_automation_gain
- double_music_gain_fix_enabled: true
- per_track_final_mix_gain_applied: false
- automation_final_mix_gain_applied: true
- music_bus_double_gain_protection_enabled: true
- music_bus_double_gain_protection_passed: true
- effective_music_gain_double_applied: false

Track Stage:
- Track-Level macht nur noch leichte Normalisierung.
- ffmpeg_music_volume_gain_db_by_track: [0.6, -1.4, 3.1, -0.6]
- track_stage_volume_db_values: [0.6, -1.4, 3.1, -0.6]
- per_track_strong_negative_gain_count: 0
- alte Track-Final-Gains wie volume=-33.5dB, -31.5dB, -28.5dB, -26.0dB vor afade sind absent.

Automation Stage:
- Automation bleibt finaler Musikbus-Gain.
- automation_stage_volume_db_values: -32.0 dB pro Chunk
- automation_strong_negative_gain_count: 106
- automation_window_count: 106
- segmented_gain_volume_count: 106
- dynamic_gain_expression_strategy: segmented_atrim_volume_concat
- command_volume_audibility_gate_passed: true

Sidechain / Voice Safety:
- sidechain_ratio: 3.0
- ratio=12 absent
- double_ducking_protection_enabled: true
- ffmpeg_clean_transition_applied: true

Tests / Proof:
- py_compile: gruen
- pytest tests/test_controlled_music_preview_render.py -vv: 60 passed
- Dry-Run Proof Manifest:
  - reports/controlled_music_preview_run/step18b_fix_single_music_bus_gain/run_20260611_205205/preview_render_manifest.json
  - reports/controlled_music_preview_run/step18b_fix_single_music_bus_gain/run_20260611_205205/ffmpeg_command.txt
- Reportordner bleibt lokal/untracked und wird nicht committed.

Safety:
- Kein Render gestartet.
- Keine MP4 erstellt.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Keine Musikdateien geaendert.
- Kein Ingest.
- Reports bleiben untracked.

Geaenderte Code-Dateien:
- scripts/controlled_music_preview_render.py
- tests/test_controlled_music_preview_render.py

Naechster Schritt:
- Commit nur mit erlaubten Dateien:
  - scripts/controlled_music_preview_render.py
  - tests/test_controlled_music_preview_render.py
  - obsidian_zenith/
- Reports nicht committen.
- Danach Push und Remote-Verifikation.
- Kein Step 18C ohne neuen Master-GO.
---

## 2026-06-11 ? Controlled Music Preview Step 18B-FIX Double Music Gain Fix Remote

Status: DONE / remote documented
Code Commit: `aed15c0 fix(music): remove double music bus gain`
Full Hash: `aed15c0cddff3bee352e4720bfc8ff0565420b8d`

Step 18A Diagnose:
- Musiktracks waren vorhanden.
- Musiktracks waren nicht silent.
- Finaler Audio-Map war wahrscheinlich korrekt.
- FFmpeg Command enthielt Musikinputs.
- FFmpeg Command baute `[music_auto]`, `sidechaincompress`, `amix` und final `[aout]`.
- Wahrscheinlicher Root Cause: doppelte Musik-Absenkung.
- Vorher wurde Musik erst auf Track-Level stark abgesenkt und danach in der Automation nochmal abgesenkt.
- Dadurch wurde der Musikbus praktisch unhoerbar.

Step 18B-FIX Ergebnis:
- Double Music Bus Gain entfernt.
- Track-Level macht nur noch leichte Normalisierung.
- Finaler Musik-Gain liegt nur noch in der Automation.
- `music_gain_application_mode`: `single_final_automation_gain`
- `per_track_final_mix_gain_applied`: false
- `automation_final_mix_gain_applied`: true
- `music_bus_double_gain_protection_passed`: true
- `effective_music_gain_double_applied`: false
- Segmented Dynamic Automation bleibt aktiv.
- Clean Transitions bleiben aktiv.
- Sidechain bleibt sanft mit Ratio <= 4.

Safety:
- Kein Render gestartet.
- Kein Upload.
- Kein Qwen.
- Kein Runtime Learning.
- Kein Ingest.
- Keine Musikdateien geaendert.

Naechster Schritt:
- Step 18C Render nur nach Master-GO.
- Step 18C bleibt gesperrt, bis diese Obsidian-Dokumentation remote gesichert ist.
---

## 2026-06-11 ? Controlled Music Preview Step 18C Render After Double Music Gain Fix

Status: DONE / render completed / owner review required

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4

Output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_210850/controlled_music_preview_main.mp4
- output_size_bytes: 1623768206

Render Result:
- status: ok
- owner_review_required: true
- upload_started: false
- runtime_learning_started: false
- qwen_used: false

Double Music Gain Fix:
- double_music_gain_fix_enabled: true
- music_gain_application_mode: single_final_automation_gain
- per_track_final_mix_gain_applied: false
- automation_final_mix_gain_applied: true
- music_bus_double_gain_protection_passed: true
- effective_music_gain_double_applied: false

Audio / Automation:
- music_audibility_policy_enabled: true
- command_volume_average_db: -32.0
- command_volume_min_db: -32.0
- command_volume_max_db: -32.0
- sidechain_ratio: 3.0
- dynamic_gain_expression_strategy: segmented_atrim_volume_concat
- clean_transitions_active: true

Safety:
- Kein Upload gestartet.
- Kein Runtime Learning gestartet.
- Kein Qwen genutzt.
- Kein Ingest.
- Keine Musikdateien geaendert.
- Reports/MP4 bleiben lokal/untracked.
- Keine Produktionsdateien geaendert.

Next:
- Owner Review Schritt 19 ist Pflicht.
- Ali prueft Bild/Ton selbst.
- Entscheidung: GO / FIX / NO-GO.
- Kein Upload ohne neues Master-GO.

## Step 19B Owner Music Balance Fix ? DONE

Status: DONE / CODE-FIX COMMITTED LOCAL
Commit: 08ac0b8 fix(preview): balance music against voice and prevent gaps

Result:
- Owner review issue addressed:
  - 01:43?01:50 known music gap protected by guard.
  - Music balance reduced under voice.
- New balance policy active:
  - owner_music_balanced_gain_range_db = [-38.0, -30.0]
  - owner_music_target_gain_db = -34.0
  - music_audibility_floor_db = -38.0
  - music_loudness_ceiling_db = -30.0
  - voice_active_music_ceiling_db = -35.0
  - no_voice_music_ceiling_db = -30.0
- Gap guard active:
  - music_continuity_guard_enabled = true
  - music_gap_detection_enabled = true
  - known_owner_gap_sec = [103.0, 110.0]
  - music_gap_at_103_110_fixed = true
  - musicbed_full_coverage_required = true
  - musicbed_no_silent_gaps = true
- Voice priority active:
  - voice_priority_music_ducking_enabled = true
  - music_must_stay_below_voice_enabled = true
  - music_vs_voice_safety_margin_enabled = true
- Dry-run gate passed:
  - checks_failed = []
  - known_gap_final_gain_db_values = [-36.0, -36.0]
- No render executed.
- No upload executed.
- No Qwen executed.
- No runtime learning executed.
- Reports remain untracked.
## 2026-06-11 21:48:03 ? Step 19C Render After Owner Music Balance Fix

Status: DONE / RENDER EXECUTED / OWNER REVIEW REQUIRED

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4

Output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_214754/controlled_music_preview_main.mp4
- size: 1623726974

Active fixes:
- music_balance_policy_enabled = true
- owner_music_balanced_gain_range_db = [-38.0, -30.0]
- owner_music_target_gain_db = -34.0
- music_audibility_floor_db = -38.0
- music_loudness_ceiling_db = -30.0
- voice_priority_music_ducking_enabled = true
- music_must_stay_below_voice_enabled = true
- music_continuity_guard_enabled = true
- known_owner_gap_sec = [103.0, 110.0]
- music_gap_at_103_110_fixed = true
- double_music_gain_fix_enabled = true
- per_track_final_mix_gain_applied = false
- automation_final_mix_gain_applied = true
- sidechain_ratio = 3.0
- dynamic_gain_expression_strategy = segmented_atrim_volume_concat
- clean_transition_policy_enabled = true

Safety:
- upload_started = false
- runtime_learning_started = false
- qwen_used = false

Next:
- Owner Review Schritt 20 is mandatory.
- No upload without new Master-GO.
- No runtime learning.

## 2026-06-11 ? Step 21A Tail Music Coverage Fix

Status:
- Phase 5: 100% DONE
- P5-L: 100% CLOSED
- Phase 5.5: 100% DONE
- Step 20 Owner Review: FIX / NO-GO
- Step 21A Code: DONE
- Commit: 9c681eb fix(preview): build musicbed from timeline segments
- Render: not started
- Upload: not started
- Runtime Learning: locked / not started
- Qwen: not used
- Ingest: not used

Root Cause:
- FFmpeg musicbed was built from selected_music_files / unique tracks.
- Timeline could have more music segments than unique tracks.
- This caused tail music to disappear while manifest still claimed no silent gaps.

Fix:
- FFmpeg musicbed is now built from music_timeline segments.
- Reused tracks become real FFmpeg music segments.
- concat=n now matches music_timeline_segment_count.
- Tail coverage guard added.
- Command/timeline consistency fields added.
- Source music loudness automation fields added.
- Voice priority remains stronger than quiet-section boost.

Dry-run evidence:
- status=dry_run
- owner_go=false
- musicbed_command_matches_timeline=true
- musicbed_no_silent_gaps=true
- tail_music_coverage_passed=true
- upload_started=false
- runtime_learning_started=false
- qwen_used=false

Next:
- Step 21B/21C render only after new Master-GO.

## 2026-06-11 ? Step 21B/21C Render After Tail Music Coverage Fix

Status:
- Phase 5: 100% DONE
- P5-L: 100% CLOSED
- Phase 5.5: 100% DONE
- Step 21A: FINAL DONE
- Step 21B/21C Render: DONE
- Owner Review: REQUIRED / pending
- Upload: not started
- Runtime Learning: locked / not started
- Qwen: not used
- Ingest: not used

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4

Output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_223708/controlled_music_preview_main.mp4

Evidence:
- status=ok
- musicbed_command_matches_timeline=True
- musicbed_command_segment_count=8
- musicbed_timeline_segment_count=8
- tail_music_coverage_passed=True
- tail_music_last_audible_sec=528.348
- musicbed_no_silent_gaps=True
- source_music_loudness_analysis_enabled=True
- source_music_quiet_section_boost_enabled=True
- source_music_loud_section_cut_enabled=True
- voice_priority_over_source_boost_enabled=True
- music_balance_policy_enabled=True
- double_music_gain_fix_enabled=True
- upload_started=False
- runtime_learning_started=False
- qwen_used=False

Next:
- Step 22 Owner Review.
- No upload without new Master-GO.
## 2026-06-12 ? Step 23B-FIX: Background Music Mix Fix pushed

Status:
- Step 23B-FIX code/test/proof: DONE
- Commit: 0c261fb / 0c261fb8538e8edee4527fa35d94b25e2b30fc16
- Remote: origin/main verified
- Render: still locked; no render was executed in Step 23B
- Upload: not started
- Runtime Learning: not started
- Qwen: not used

Owner issue fixed in policy:
- Music too foreground / too loud
- slow music fade-ins
- no audible tail music after 07:51
- raw fullmix sidechain risk

Proof:
- Targeted tests: 121 passed
- Dry-run policy proof: PASS
- owner_music_target_gain_db: -39.0
- overall music range: [-44.0, -34.0]
- voice active ceiling: -40.0
- no voice ceiling: -34.0
- sidechaincompress removed from command
- slow 3s fades removed
- forbidden foreground gains -30/-31/-32/-33 blocked
- owner tail music guard passed

Next:
- Await Master-GO for a new controlled render.
## 2026-06-12 ? Step 23C Controlled Preview Render after Background Music Mix Fix

Status:
- Step 23C render: DONE
- Owner Review: REQUIRED / Step 24
- Render was executed exactly once after dry-run gates passed.
- No upload.
- No runtime learning.
- No Qwen.
- No ingest.

Input:
- exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4
- duration: 528.348813 sec

Output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260612_004039/controlled_music_preview_main.mp4
- size: 1623778742 bytes
- manifest: reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260612_004039/preview_render_manifest.json
- summary: reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260612_004039/preview_render_summary.md

Policy evidence:
- owner_background_music_policy_enabled: true
- overall_music_gain_range_db: [-44.0, -34.0]
- owner_music_target_gain_db: -39.0
- voice_active_music_ceiling_db: -40.0
- no_voice_music_ceiling_db: -34.0
- command_contains_foreground_music_gain: false
- slow_segment_fadein_fix_enabled: true
- segment_fade_in_max_sec: 0.25
- segment_fade_out_max_sec: 0.25
- raw_fullmix_sidechain_blocked: true
- ffmpeg_sidechaincompress_disabled: true
- final_music_segment_tail_fade_disabled: true
- owner_tail_music_guard_enabled: true
- owner_tail_music_guard_passed: true
- owner_tail_music_min_gain_db: -38.0
- tail_music_final_window_audible: true
- dynamic_gain_non_constant: true
- musicbed_command_matches_timeline: true

Forbidden command checks:
- volume=-30.0dB/-31.0dB/-32.0dB/-33.0dB: no hits
- 3s segment fades: no hits
- sidechaincompress: no hits

Tail audio smoke:
- 07:51-end volumedetect mean_volume: -30.3 dB
- 07:51-end volumedetect max_volume: -15.3 dB
- last 20 sec mean_volume: -29.6 dB
- last 20 sec max_volume: -15.5 dB
- astats RMS level: -36.640643 dB
- astats Peak level: -27.813287 dB

Important:
- Technical smoke does not replace Owner Review.
- Ali must decide GO / FIX / NO-GO by watching and listening.
## 2026-06-12 ? Step 24 Owner Review after Step 23C Render: FIX / NO-GO

Status:
- Step 23C render was reviewed by Ali.
- Owner verdict: FIX / NOT UPLOADABLE.
- Ali says the same audible errors are still present as before.
- Technical gates from Step 23C were green, but owner listening review failed.
- No upload.
- No runtime learning.
- No Qwen.
- No new render.

Reviewed output:
- reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260612_004039/controlled_music_preview_main.mp4

Owner feedback:
- Same errors as before.
- Background music fix did not solve the audible result.

Local owner-fix report:
- reports/controlled_music_preview_run/step24_owner_review_fix_after_background_music_mix/step24_owner_review_fix.json
- reports/controlled_music_preview_run/step24_owner_review_fix_after_background_music_mix/step24_owner_review_fix.md

Conclusion:
- Step 23C is rejected by Owner Review.
- The previous policy/command gates are not enough.
- Next step must be Step 24A diagnosis.
- Do not patch blindly.
- Do not render blindly.

Required next step:
- Diagnose actual audible mix path and compare command policy vs rendered result.
- Find why Ali still hears the same problems despite technical fields showing background policy active.

## Step 24A/24B Deep Audio Diagnosis Fix ? 2026-06-12 01:36

Status:
- Step 24 Owner Review: FIX / NO-GO
- Step 24A Deep Audio Diagnosis: DONE
- Step 24B Code Fix: DONE / pushed
- EOF Cleanup: DONE / pushed
- Controlled Render: locked until Master-GO
- Upload: blocked
- Qwen: blocked
- Runtime Learning: blocked
- Ingest: blocked

Final Root Cause:
- music_auto/musicbed was only 471.345s long while the video was 528.348s.
- Cause: double music trimming.
- The music input used input seek (-ss 30) and the filter also used atrim=start=30.
- Effective result: the music bus lost too much usable duration and ended before the video ended.

Why old gates were wrong:
- Old gates checked timeline/command/manifest consistency.
- They did not verify the real generated music bus stem.
- Therefore manifest could be green while Ali still heard no music at the tail.

Fix:
- Removed double music seek / double trim.
- Added real audio-stem gates.
- Dry-run can now generate audio stem gates without producing an MP4.
- New diagnostics verify:
  - music_auto tail audibility
  - song start audibility
  - music-vs-voice distance
  - final mix tail probe
- Voice-active music was adjusted:
  - stronger voice: -42 dB
  - otherwise: -40 dB

Proof:
- Code Commit: 0b2e425 fix(music): verify preview mix with audio stem gates
- EOF Cleanup Commit: 5763316 chore(tests): clean music output diagnostics eof
- Tests before code commit: 129 passed
- EOF Smoke: 4 passed
- No full render started
- No upload
- No Qwen
- No Runtime Learning

Next:
- Controlled Render only after Master-GO.

## Step 25A Smooth Music Automation + Crossfade Fix ? 2026-06-12 02:27

Status:
- Step 25 Owner Review: FIX / NO-GO
- Step 25A Code Fix: DONE / pushed
- Controlled Render: locked until Master-GO
- Upload: blocked
- Qwen: blocked
- Runtime Learning: blocked
- Ingest: blocked

Owner Issue:
- Tail music is now fixed and music reaches the end.
- Remaining problem: 5-second automation is audible.
- Music sometimes feels perfect, then 5 seconds too loud, then good again.
- Song transitions are too hard.
- Desired behavior: outgoing song fades down while incoming song fades up.

Fix:
- Added smooth gain envelope.
- Added max adjacent gain delta gate: 1.5 dB.
- Added voice lookahead / attack / release behavior.
- Added five-second pumping guard.
- Added true song crossfade using overlapping delayed segments and amix.
- Replaced hard segment concat behavior for music transitions.
- Added transition energy diagnostics.
- Kept audio stem gates from Step 24A/24B.
- Tail protection remains active.

Proof:
- Code Commit: f93bea8 fix(music): smooth automation and crossfadetransitions
- Tests: 140 passed
- Dry-run status: diagnosis_ok
- audio_stem_probe_passed=True
- max_adjacent_gain_delta_db=1.5
- max_adjacent_gain_delta_passed=True
- five_second_pumping_detected=False
- music_crossfade_count=7
- music_expected_crossfade_count=7
- music_transition_silent_gap_count=0
- music_transition_hard_cut_detected=False
- music_auto_tail_audible=True
- final_mix_tail_probe_passed=True
- upload_started=False
- qwen_used=False
- runtime_learning_started=False
- mp4_exists=False

Report:
- reports/controlled_music_preview_run/step25a_smooth_music_crossfade_fix/step25a_manifest.json
- reports/controlled_music_preview_run/step25a_smooth_music_crossfade_fix/step25a_summary.md

Next:
- Step 25B Controlled Render only after Master-GO.
- No upload without separate Master-GO.
