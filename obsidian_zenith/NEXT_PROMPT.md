PROJECT ZENITH — CONTROLLED MUSIC PREVIEW RUN — SCHRITT 16B-R2 — EXECUTE RENDER NACH SEGMENTED-GAIN-FIX

ROLLE:
Bauchat/Engineer.
Ali führt lokal aus.

AKTUELLER STATUS:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5 Infrastruktur: 100% / DONE
- Step 16B-R-FIX: DONE / remote gesichert
- Runtime Learning: locked

LETZTER REMOTE-COMMIT:
- `efaff10` fix(preview): replace nested music gain expression
- Full Hash: `efaff1049c2784d894c0a12e090e788e62da672d`

WAS WURDE GEFIXT:
Die alte 106-fach verschachtelte FFmpeg-Volume-Expression mit `if(between(t,...))` wurde ersetzt durch FFmpeg-sichere segmentierte Gain-Automation:

- Strategie: `segmented_atrim_volume_concat`
- `[musicbed]asplit=106[...]`
- pro Fenster: `atrim=start=...:end=...,asetpts=PTS-STARTPTS,volume=-39.0dB`
- danach: `[ag0]...[ag105]concat=n=106:v=0:a=1[music_auto]`

BEWIESEN:
- Tests gruen: `tests/test_controlled_music_preview_render.py` = `52 passed`
- Dry-Run gruen
- `status=dry_run`
- `owner_execute_required=true`
- `owner_go=false`
- `dynamic_gain_expression_strategy=segmented_atrim_volume_concat`
- `segmented_gain_asplit_count=106`
- `segmented_gain_atrim_count=106`
- `segmented_gain_volume_count=106`
- `command_contains_nested_if_volume_automation=false`
- `manifest_command_consistency_gate=true`
- Forbidden/Nested Command Check leer
- Kein neuer MP4 im 17:12 Dry-Run
- Kein Upload
- Kein Qwen
- Kein Runtime Learning

WICHTIG:
Step 16B-R-FIX ist nur Code/Dry-Run-Fix.
Der echte Execute-Render darf erst in Schritt 16B-R2 mit neuem Master-GO laufen.

ZIEL NÄCHSTER SCHRITT:
Schritt 16B-R2 soll den echten kontrollierten Execute-Render mit der neuen segmented-gain FFmpeg-Strategie ausführen und danach Owner Review vorbereiten.

VERBOTEN OHNE MASTER-GO:
- kein Render
- kein Execute
- kein Upload
- kein Runtime Learning
- kein Qwen
- kein Qwen-Autocut
- kein Ingest
- keine Musikdateien ändern/committen
- keine Produktionsdateien überschreiben
- kein `git add .`
- kein `git add -A`

ERLAUBT NACH MASTER-GO:
- exakt kontrollierter Execute-Render für den bestätigten Visual Proper Run:
  `exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4`
- Output-Root bleibt:
  `reports/controlled_music_preview_run/step13_visual_proper_run_music_render`
- danach Manifest/Command/MP4/Safety prüfen
- Owner Review vorbereiten
