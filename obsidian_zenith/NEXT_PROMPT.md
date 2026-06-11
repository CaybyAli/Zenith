PROJECT ZENITH — CONTROLLED MUSIC PREVIEW RUN — SCHRITT 16B-FIX — REAL FFMPEG CLEAN TRANSITIONS + DYNAMIC AUTOMATION COMMAND

Nur nach Master-GO.

Aktueller Stand:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5 Infrastruktur: 100% / DONE
- Step 16A Dynamic Music Automation Planner: DONE / CODE-GO
- Step 16B Render: STOPP vor Execute
- Grund: clean_transition_policy_enabled=true, aber FFMPEG Command ohne afade/acrossfade

Ziel:
Kein Render.
Erst echte Command-Abbildung bauen/testen:
- Clean song transitions müssen im FFMPEG-Command sichtbar sein
- 3s Crossfade oder saubere Fade-Übergänge
- 30s Track-Intro vermeiden
- 15s Track-Outro vermeiden
- Dynamic Music Automation muss als echte Gain-Kurve/Segmentsteuerung im Command sichtbar werden
- 5s Fensteranalyse bedeutet Lautstärkeplanung, nicht Songwechsel alle 5s

Pflicht:
- kein Upload
- kein Runtime Learning
- kein Qwen
- kein Ingest
- keine Musikdateien löschen/kopieren/committen
- keine video_configs ändern
- keine learning_corpus ändern
- kein git add .
- kein git add -A

Nächster Render erst nach neuem Dry-Run-Command-Gate.
