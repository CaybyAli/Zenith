# SAFETY INDEX

Stand: 2026-06-06

## Zentrale Safety-Regeln

- Kein Render in P5-L6.5.
- Kein Preview-Render in P5-L6.5.
- Kein Ingest in P5-L6.5.
- Kein Musik-Build ohne eigenes Master-GO.
- Kein Preview-Render ohne eigenes Gate.
- Kein echter Learning-Loop.
- Kein echter Overnight-Dauerlauf.
- Kein Qwen-Autocut.
- Qwen bleibt `analysis_only`.
- Qwen bleibt `can_cut=false`.
- Reports bleiben untracked.
- Keine Produktionsdateien ueberschreiben.
- Keine `video_configs` oder `learning_corpus` Writes ohne eigenes Gate.
- Keine Datei-Loeschung ohne ausdrueckliche Erlaubnis.
- Echte Loop-Starts nur mit Master-GO, Enable-Flag, Stop-Schalter, Timeout und Manifest.

## Git-Regeln

- Nie `git add .`.
- Nie `git add -A`.
- Keine Reports committen, ausser Master erlaubt es explizit.
- Nur explizit erlaubten Scope stagen.
- Bestehende untracked Altlasten nicht anfassen.

## Aktueller Gate

P5-L ist geschlossen: 100% / CLOSED.

Runtime Learning Gate: locked / later.

Naechster Gate: 5.5-3 Energy-to-Music Mapping, nur nach Master-GO.

Runtime Learning Gate bleibt gesperrt.
Phase 5.5 Musik-Contracts sind abgeschlossen: 30%.
Musik-Build bleibt gesperrt.

## 5D Qwen Kontrollrun Ergebnis

- Modell: `qwen3.6:latest`.
- `qwen_used=true`.
- `qwen_visible_response=true`.
- `qwen_role=analysis_only`.
- `qwen_can_cut=false`.
- `qwen_autocut_allowed=false`.
- `dangerous_response_detected=false`.
- `render_used=false`.
- `ingest_used=false`.
- `music_used=false`.
- `autocut_used=false`.
- `learning_loop_started=false`.
- `phase_5_5_used=false`.

## 5F Close Safety

- P5-L geschlossen.
- Runtime Learning Gate locked.
- Phase 5.5 Musik weiterhin locked.
- Kein Qwen gestartet.
- Kein Render.
- Kein Ingest.
- Keine Musik.
- Kein echter Learning-Loop.

## Phase 5.5 Musik Safety

- Safety-Regeln: [[Phase5_5_Safety_Rules]]
- Library-Regeln: [[Phase5_5_Music_Library_Rules]]
- Musikquellen spaeter nur lokal und Owner-freigegeben.
- Keine externen Musikdownloads.
- Keine API-Keys.
- Keine copyrighted Musik automatisch verwenden.
- Keine Musikdateien in Git committen.
- Qwen bleibt ohne Autocut-Rechte.
- Qwen darf spaeter hoechstens Stimmung, Energie, Risiken und Vorschlaege beschreiben.
- Qwen darf nicht schneiden, rendern, Musik final auswaehlen oder externe Quellen nutzen.
- Vor jedem Musik-Run: Enable-Flag, klarer Output-Ordner, Manifest, Safety Flags, Owner Review.

## Phase 5.5-1 Inventory Safety

- Gefundene Musik-Kandidaten sind nicht tracked und duerfen nicht committed werden.
- Getrackte Audio-Dateien sind SFX/Test-Fixtures, keine Musikbibliothek.
- Lokale Musik nur mit Owner-Freigabe und klarem Lizenzstatus.
- `.gitignore` schuetzt bereits `.wav`, `.mp3`, `.flac`, `assets/**/*.wav`, `assets/**/*.mp3`, `tmp/`, `preprocessed/`, `data/` und `scratch/`.
- Spaeteres Gitignore-Risiko: `local_assets/music/`, `.m4a`, `.aac`, `.ogg`, `.opus` brauchen vor Nutzung eigene Regeln.
- Heute keine `.gitignore`-Aenderung.

## Phase 5.5-2 Contracts Safety

- Contract-Code: `core/music_contracts.py`
- Smoke Script: `scripts/p55_music_contracts_smoke.py`
- Manifest-Pflicht ist technisch vorbereitet.
- Erlaubte Kategorien: `intro`, `background`, `peak`, `outro`.
- Erlaubte Roots: `local_assets/music`, `assets/audio/gaming_main/music`, `assets/music`.
- Owner-Freigabe Pflicht.
- Lizenzklarheit Pflicht.
- Forbidden License Status wird geblockt: `unknown`, `copyrighted_unknown`, `missing`.
- Gitignore-Schutz jetzt vorhanden:
  - `local_assets/music/`
  - `*.m4a`
  - `*.aac`
  - `*.ogg`
  - `*.opus`
- Smoke Output ist auf `reports/phase5_5_music_contracts` begrenzt.
- Reports bleiben untracked.
- Musik-Build bleibt `false`.
