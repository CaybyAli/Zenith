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
- 0% / locked.
- Phase 5.5 ist NICHT Learning.
- Musik wurde NICHT gestartet.

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
- [[NEXT_PROMPT]]
