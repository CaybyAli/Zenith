# ARCHITECTURE MAP

Stand: 2026-06-06

## Drei getrennte Bereiche

### Phase 5

Phase 5 ist die Video-Pipeline-Finalisierung.

Status:
- 100% / DONE / FINAL-GO.
- Alle 8 Endkriterien sind DONE.
- K7 Kontroll-Run + Ali-Freigabe ist DONE.

### P5-L

P5-L ist die Post-Phase-5 Learning-Vorbereitung.

Status:
- 100% / CLOSED.
- P5-L0 bis P5-L6 sind DONE.
- P5-L6.5 5A bis 5F sind DONE.
- P5-L ist Vorbereitung, kein Runtime-Run.
- P5-L7 / Schlaf-Learning-Run ist als Runtime Learning Gate / later / locked ausgelagert.

### Runtime Learning Gate

Runtime Learning Gate ist ein spaeterer Betriebsbereich fuer echten Schlaf-/Learning-Run.

Status:
- later / locked.
- Nur mit eigenem Master-GO.
- Kein Autocut.
- Kein Render.
- Kein Ingest.
- Keine Musik.

### Phase 5.5

Phase 5.5 ist Musik-Integration.

Status:
- 45% / Energy-Mood-Channel Mapping.
- Phase 5.5 ist NICHT Learning.
- Phase 5.5 ist als Planungsbereich geoeffnet.
- Musik-Inventory ist abgeschlossen.
- Musik-Contracts sind abgeschlossen.
- Energy-to-Music Mapping ist abgeschlossen.
- Main/Uncut Mood Patch ist abgeschlossen.
- Musik-Build wurde NICHT gestartet.
- Preview-Run wurde NICHT gestartet.
- Runtime Learning bleibt getrennt und locked / later.

Geplanter Bereich:
- lokale Musikquellen inventarisieren
- Musik-Manifest und Safety-Flags definieren
- Energie/Emotion/Highlight zu Musik abbilden
- Main Account und Uncut als getrennte Channel-Regeln validieren
- Ducking und Audio-Mix-Regeln vorbereiten
- kontrollierten Musik-Preview spaeter nur mit eigenem Master-GO starten

Musik-Inventory:
- Lokale Musik-Kandidaten: `assets/audio/gaming_main/music/*.mp3`
- Leerer Platzhalter: `assets/music/.gitkeep`
- Spaetere lokale Bibliothek empfohlen: `local_assets/music/`
- Musikdateien bleiben ausserhalb Git.
- Nur Metadaten/Manifeste duerfen spaeter kontrolliert dokumentiert werden.

Musik-Contracts:
- Erster Code-Safety-Baustein: `core/music_contracts.py`
- Smoke/Manifest-Check: `scripts/p55_music_contracts_smoke.py`
- Erlaubte Kategorien und lokale Roots sind zentral definiert.
- Owner-/Lizenzpflicht ist zentral validiert.
- Safety-Flags erzwingen: kein Musik-Build, kein Render, kein Ingest, kein Qwen-Autocut, kein Runtime Learning.
- Reports gehen nur nach `reports/phase5_5_music_contracts` und bleiben untracked.

Energy-to-Music Mapping:
- Mapping-Baustein: `core/music_energy_mapping.py`
- Position: nach Musik-Contracts, vor Musik-Selector und Ducking.
- Segmentrolle, Energie, Highlight-Score, Speech-Density und Mood werden validiert.
- Ergebnis ist nur eine Musik-Kategorie: `intro`, `background`, `peak`, `outro`, `funny`, `suspense`, `calm`, `hype`, `victory`, `emotional` oder fuer Uncut `none`.
- Channel-Regel:
  - Main Account darf spaeter Musik mappen, nur mit Safety/Owner/Lizenz/Manifest.
  - Uncut blockiert Musik immer: `music_allowed=false`, `music_category=none`.
- Ducking wird nur als Flag geplant, noch nicht gebaut.
- Keine Musikdatei wird gelesen, gewaehlt oder eingefuegt.

## Qwen

Qwen ist ein Analyse-Side-Track.

Qwen darf:
- analysieren
- kommentieren
- strukturierte JSON-Antworten liefern

Qwen darf nicht:
- schneiden
- rendern
- ingesten
- Musik nutzen
- Timelines bauen
- Autocut ausloesen

## Obsidian

Obsidian ist der Truth Store / Second Brain.

Wichtige Dateien:
- [[CURRENT_TRUTH]]
- [[Phase_Status]]
- [[GO_NO_GO_Log]]
- [[Script_Index]]
- [[Safety_Index]]
- [[P5L_Runbook]]
- [[P5L_Close_Report]]
- [[Runtime_Learning_Gate]]
- [[Phase5_5_Opening_Gate]]
- [[Phase5_5_Safety_Rules]]
- [[Phase5_5_Backlog]]
- [[Phase5_5_Run_Log]]
- [[Phase5_5_Music_Inventory]]
- [[Phase5_5_Music_Library_Rules]]
- [[NEXT_PROMPT]]
