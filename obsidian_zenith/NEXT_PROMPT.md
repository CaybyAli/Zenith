PROJECT ZENITH — CONTROLLED MUSIC PREVIEW RUN — SCHRITT 16B-R-FIX — FFMPEG-SAFE DYNAMIC VOLUME AUTOMATION

ROLLE:
Bauchat/Engineer.
Ali führt lokal aus.

AKTUELLER STATUS:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5 Infrastruktur: 100% / DONE
- Step 16B-FIX: DONE
- Step 16B-R Execute Render: FAILED / STOPP
- Runtime Learning: locked

LETZTER FEHLER:
FFmpeg Execute scheitert im Volume-Eval-Parser.

Failed Run:
reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260611_165114

Kernfehler:
- Parsed_volume Eval
- Missing ')' or too many args
- Ursache: 106-fach verschachtelte if(between(t,...)) Dynamic-Gain-Expression ist für echten FFmpeg-Execute nicht robust.

WICHTIG:
Dry-Run Command-Gate war grün.
Der Fehler kommt erst beim echten FFmpeg-Parser.

ZIEL NÄCHSTER SCHRITT:
Dynamic 5s Music Automation FFmpeg-sicher realisieren, ohne lange nested if(between(...)) Expression.

Mögliche Richtung:
- FFmpeg-sichere segmentierte Filterstrategie
- oder kürzere/einfachere Volume-Automation-Expression
- oder mehrere kleinere Audio-Segmente mit je eigener Gain-Expression
- Manifest-Command-Consistency Gate muss weiter ehrlich bleiben

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
