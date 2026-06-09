# ARCHITECTURE MAP

Stand: 2026-06-09

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
- 75% / Ducking Plan abgeschlossen.
- Phase 5.5 ist NICHT Learning.
- Phase 5.5 ist als Planungsbereich geoeffnet.
- Musik-Inventory ist abgeschlossen.
- Musik-Contracts sind abgeschlossen.
- Energy-to-Music Mapping ist abgeschlossen.
- Main/Uncut Mood Patch ist abgeschlossen.
- Musik-Selector ist abgeschlossen.
- Ali-Musikordner-Taxonomie ist abgeschlossen.
- Lokale Main-Musikbibliothek ist verifiziert.
- Ducking Plan ist abgeschlossen.
- Musik-Build wurde NICHT gestartet.
- Echter Audio-Mix wurde NICHT gestartet.
- Preview-Run wurde NICHT gestartet.
- Runtime Learning bleibt getrennt und locked / later.

Geplanter Bereich:
- lokale Musikquellen inventarisieren
- Musik-Manifest und Safety-Flags definieren
- Energie/Emotion/Highlight zu Musik abbilden
- Main Account und Uncut als getrennte Channel-Regeln validieren
- passende Main-Account-Musik-Metadaten selektieren
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
- Ergebnis ist nur eine Musik-Kategorie: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad` oder fuer Uncut `none`.
- Deprecated Mood-Aliasse:
  - `suspense` -> `hype`
  - `calm`, `neutral`, default gameplay -> `vlog_background`
  - `funny` -> `funny_gaming_background`
- Channel-Regel:
  - Main Account darf spaeter Musik mappen, nur mit Safety/Owner/Lizenz/Manifest.
  - Uncut blockiert Musik immer: `music_allowed=false`, `music_category=none`.
- Ducking wird nur als Flag geplant, noch nicht gebaut.
- Keine Musikdatei wird gelesen, gewaehlt oder eingefuegt.

Musik-Selector:
- Selector-Baustein: `core/music_selector.py`
- Position: Contracts -> Energy/Mood/Channel Mapping -> Selector -> Ducking Plan -> Controlled Preview.
- Der Selector arbeitet nur mit Metadaten.
- Main Account kann sichere Kandidaten selektieren.
- Uncut wird immer blockiert.
- Missing Category erzeugt `missing_candidate`, ohne heimlichen Fallback.
- Keine Musikdatei wird gelesen, geoeffnet, kopiert oder eingefuegt.

Ducking Plan:
- Ducking-Baustein: `core/music_ducking_plan.py`
- Position: Contracts -> Mapping -> Selector -> Ducking Plan -> Controlled Preview.
- Der Ducking Plan arbeitet nur mit Segment-/Selection-Metadaten.
- Main Account kann sichere Ducking-Werte planen.
- Uncut wird immer blockiert: `music_allowed=false`, `selected_category=none`, `plan_status=blocked`.
- Missing Candidate erzeugt `no_selected_music`.
- Speech Priority:
  - low: base `-17.0`, duck `-22.0`, max `-15.0`
  - medium: base `-20.0`, duck `-26.0`, max `-18.0`
  - high: base `-23.0`, duck `-30.0`, max `-21.0`
  - very_high: base `-26.0`, duck `-34.0`, max `-24.0`
- Ali/Friend-Stimmen haben Vorrang.
- `max_music_gain_db` darf nie lauter als `-14.0` werden.
- Keine Musikdatei wird gelesen, geoeffnet, kopiert oder eingefuegt.
- Kein echter Audio-Mix wird gestartet.

Lokale Main-Account-Musikstruktur:
- Offizielle Ordner unter `local_assets/music/main_account/`:
  - `intro`
  - `outro`
  - `vlog_background`
  - `funny_gaming_background`
  - `fail`
  - `hype`
  - `sad`
- `hype` bedeutet spannend / Action / Peak / Clutch.
- Alte Ordner `funny`, `suspense`, `calm`, `victory`, `emotional`, `background`, `peak` sind deprecated, falls lokal vorhanden.
- Kein `local_assets/music/uncut`.

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
