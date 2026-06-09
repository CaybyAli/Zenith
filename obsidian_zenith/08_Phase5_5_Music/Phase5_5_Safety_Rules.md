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
- nur offizielle Kategorien:
  - `intro`
  - `outro`
  - `vlog_background`
  - `funny_gaming_background`
  - `fail`
  - `hype`
  - `sad`
- `hype` bedeutet spannend / Action / Peak / Clutch

## Channel-Regeln

- Main Account darf spaeter Musik bekommen, nur mit Safety/Owner/Lizenz/Manifest.
- Uncut bekommt niemals Musik.
- Uncut bekommt keine Intro-Musik.
- Uncut bekommt keine Hintergrundmusik.
- Uncut bekommt keine Hype-/Action-/Peak-Musik.
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
- Der Ducking Plan darf nur Lautstaerke planen, keine Audio-Dateien veraendern.

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
- Offizielle Zielkategorien: `intro`, `outro`, `vlog_background`, `funny_gaming_background`, `fail`, `hype`, `sad`.
- Deprecated Mood-Aliasse:
  - `suspense` -> `hype`
  - `funny` -> `funny_gaming_background`
  - `calm`, `neutral`, default gameplay -> `vlog_background`
- Main Account darf spaeter Kategorien mappen.
- Uncut muss immer `music_allowed=false` und `music_category=none` bleiben.
- Es darf keine Musik einfuegen.
- Es darf keine Musikdatei lesen oder auswaehlen.
- Es darf keinen Render oder Preview-Render starten.
- Ducking bleibt nur ein Flag bis eigenes Gate.

## Musik-Selector

- Selector-Code: `core/music_selector.py`
- Selector darf nur Metadaten waehlen.
- Selector darf nur die offiziellen Main-Kategorien selektieren.
- Selector darf keine Musikdateien lesen.
- Selector darf keine Musikdateien oeffnen.
- Selector darf keine Musikdateien kopieren.
- Selector darf keine Musikdateien einfuegen.
- Selector darf keine echte Videoauswahl finalisieren.
- Main Account ist erlaubt, wenn Owner, Lizenz, Root und Kategorie passen.
- Uncut wird immer blockiert.
- Missing Category darf nicht heimlich fallbacken.

## Ducking Plan

- Ducking Plan Code: `core/music_ducking_plan.py`
- Ducking Plan darf nur Lautstaerke planen, keine Audio-Dateien veraendern.
- Kein echter Audio-Mix.
- Keine Musikdateien lesen, oeffnen, kopieren, loeschen oder konvertieren.
- Main Account darf Ducking planen.
- Uncut wird immer blockiert.
- Ali/Friend-Stimmen haben Vorrang.
- `max_music_gain_db` darf nie lauter als `-14.0` werden.
- Hype/Fail/Funny duerfen Musik nicht automatisch zu laut setzen.
- Missing Candidate erzeugt `no_selected_music`.
- Smoke Output nur unter `reports/phase5_5_ducking_plan`.
