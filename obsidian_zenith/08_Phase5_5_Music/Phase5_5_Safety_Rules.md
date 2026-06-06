# Phase 5.5 Safety Rules

## Harte Verbote

- kein Render ohne Master-GO
- kein Preview-Render ohne eigenes Gate
- kein Ingest
- kein Qwen-Autocut
- kein Runtime Learning
- keine Phase-5-Codeaenderung ohne eigenes Gate
- keine externen Musikdownloads
- keine API-Keys
- keine copyrighted Musik automatisch verwenden
- keine Produktionsdateien ueberschreiben
- keine Musikdateien in Git committen
- Uncut bekommt niemals Musik
- keine Reports committen, ausser Master erlaubt es ausdruecklich

## Musik-Quellen

Library-Regeln: [[Phase5_5_Music_Library_Rules]]

Erlaubt spaeter nur:
- lokale Musikdateien
- vom Owner bewusst bereitgestellt
- klare Lizenz / Owner-Freigabe
- keine automatischen Downloads
- nur fuer Main Account

## Channel-Regeln

- Main Account darf spaeter Musik bekommen, nur mit Safety/Owner/Lizenz/Manifest.
- Uncut bekommt niemals Musik.
- Uncut bekommt keine Intro-Musik.
- Uncut bekommt keine Hintergrundmusik.
- Uncut bekommt keine Peak-Musik.
- Uncut bekommt keine Outro-Musik.
- Uncut ignoriert Mood, Energy und Highlight fuer Musik.

## Qwen-Regeln

Qwen darf spaeter hoechstens:
- Musikstimmung beschreiben
- Energie-Level kommentieren
- Risiken nennen
- Vorschlaege machen

Qwen darf nicht:
- schneiden
- rendern
- Musik final auswaehlen ohne Regelwerk
- Autocut ausloesen
- Dateien frei aendern
- externe Quellen nutzen
- die Uncut-Musik-Sperre aendern

## Audio-Regeln

Musik darf:
- Stimme nicht verdecken
- Ali nicht unverstaendlich machen
- Friend nicht unverstaendlich machen
- nicht uebersteuern
- keine harten Lautstaerke-Spruenge erzeugen

## Pflicht vor jedem Musik-Run

- Enable-Flag
- Output-Ordner klar
- Manifest Pflicht
- Safety Flags Pflicht
- Owner Review Pflicht

## Contracts / Manifest

- Contract-Code: `core/music_contracts.py`
- Smoke Script: `scripts/p55_music_contracts_smoke.py`
- Manifest-Pflicht: `music_contracts_manifest.json`
- Safety-Flags muessen zeigen:
  - `music_build_started=false`
  - `music_inserted=false`
  - `render_used=false`
  - `preview_render_used=false`
  - `ingest_used=false`
  - `qwen_autocut_used=false`
  - `runtime_learning_started=false`
  - `music_files_committed=false`

## Energy-to-Music Mapping

- Mapping-Code: `core/music_energy_mapping.py`
- Energy-to-Music Mapping darf nur Kategorien planen.
- Main Account darf spaeter Kategorien mappen.
- Uncut muss immer `music_allowed=false` und `music_category=none` bleiben.
- Es darf keine Musik einfuegen.
- Es darf keine Musikdatei lesen oder auswaehlen.
- Es darf keinen Render oder Preview-Render starten.
- Ducking bleibt nur ein Flag bis eigenes Gate.
