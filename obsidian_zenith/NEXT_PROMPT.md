PROJECT ZENITH — CONTROLLED MUSIC PREVIEW — SCHRITT 18B-FIX — FIX MUSIC ROUTING / MIX PRESENCE

Nur nach Master-GO.

Status:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5 Infrastruktur: 100% / DONE
- Controlled Music Preview Schritt 18A: DONE / diagnosis only
- Runtime Learning: locked

Owner Review:
- Entscheidung: FIX
- Problem: Musik ist gar nicht hörbar
- Stimmen/Game sind hörbar

Step 18A Root Cause Diagnose:
- Output Audio Stream existiert
- Musiktracks existieren und sind nicht silent
- FFmpeg Command enthält Musikinputs
- FFmpeg Command baut [music_auto]
- FFmpeg Command enthält sidechaincompress
- FFmpeg Command enthält amix
- Finaler Audio-Map nutzt [aout]
- Falscher finaler Audio-Map ist unwahrscheinlich
- Stärkster Verdacht: doppelte Musik-Absenkung im Musikbus
  - Tracks erst ca. -26.9 dB bis -31.4 dB
  - danach Automation-Chunks nochmal volume=-32.0dB
  - Musikbus dadurch effektiv ca. -59 bis -63 dB und praktisch unhörbar
- Output ist in Mess-Samples ca. 6 dB leiser als Input

Ziel:
Root Cause aus Step 18A beheben:
- Musik wird im finalen Output hörbar
- finaler Audio-Stream muss gemischtes Audio mappen
- Musikbus darf nicht effektiv silent sein
- amix/sidechain darf Musik nicht komplett killen
- keine blinde Lautstärke-Erhöhung ohne Routing-Beweis

Verbote:
- Kein Render ohne neues GO
- Kein Upload
- Kein Runtime Learning
- Kein Qwen
- Keine Musikdateien löschen/ändern
- Kein Scope-Drift
