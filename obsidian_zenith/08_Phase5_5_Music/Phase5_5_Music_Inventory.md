# Phase 5.5 Music Inventory

Stand: 2026-06-06

## Status

- Phase 5.5: 15% / Musik-Inventory
- Musik-Build: noch NICHT gestartet
- Render: nicht gestartet
- Preview-Render: nicht gestartet
- Qwen: nicht gestartet
- Runtime Learning: locked / later

## Gefundene lokale Musikquellen

Repo-Scan nur lesend:
- Gesamt gefundene Audiodateien: 699
- Dateitypen: 5 `.mp3`, 694 `.wav`
- Hauptbereiche:
  - `.venv_whisperx_p5_2`: 23 Audio-Test-/Paketdateien
  - `_p2_6_audio_probe`: 1 Audio-Probe
  - `assets`: 5 Audiodateien
  - `data`: 2 Voice-Reference-Dateien
  - `preprocessed`: 216 Audio-Artefakte
  - `reports`: 434 Audio-Artefakte
  - `scratch`: 4 Audio-Artefakte
  - `tests`: 4 Audio-Fixtures
  - `tmp`: 10 Audio-Artefakte

Gefundene Musik-Kandidaten:

| Pfad | Typ | Groesse | Tracking |
|---|---:|---:|---|
| `assets/audio/gaming_main/music/main_calm_bed.mp3` | `.mp3` | 64592 bytes | nicht tracked, durch `.gitignore` ignoriert |
| `assets/audio/gaming_main/music/main_intro_bed.mp3` | `.mp3` | 64592 bytes | nicht tracked, durch `.gitignore` ignoriert |
| `tmp/music_apply_processor_partial_apply_smoke/music_track_existing.mp3` | `.mp3` | 40560 bytes | nicht tracked, `tmp/` ignoriert |
| `tmp/music_apply_processor_smoke/music_track_1.mp3` | `.mp3` | 40560 bytes | nicht tracked, `tmp/` ignoriert |
| `tmp/music_apply_processor_smoke/music_track_2.mp3` | `.mp3` | 40560 bytes | nicht tracked, `tmp/` ignoriert |

Weitere relevante lokale Struktur:
- `assets/music/.gitkeep` ist getrackt und dient als leerer Platzhalter.
- `assets/music/` enthaelt aktuell keine Musikdateien.
- `assets/sfx/censor/*.wav` sind getrackte SFX-Dateien, aber keine Musikbibliothek.
- `tests/fixtures/*.wav` sind getrackte Test-Fixtures, aber keine Musikbibliothek.
- `preprocessed/`, `reports/`, `scratch/`, `tmp/` enthalten Audio-Artefakte, sind aber keine erlaubte Musikquelle fuer Phase 5.5.

## Bewertung

- Nutzbare lokale Musik ist nur als Kandidat vorhanden: `assets/audio/gaming_main/music/main_calm_bed.mp3` und `main_intro_bed.mp3`.
- Lizenz-/Owner-Freigabe ist fuer diese Kandidaten noch nicht dokumentiert.
- Audiodateien sind teils bereits getrackt: `assets/sfx/censor/*.wav` und drei `tests/fixtures/*.wav`.
- Die gefundenen MP3-Musikdateien sind nicht getrackt und durch `.gitignore` geschuetzt.
- Git-Risiko bleibt bestehen, weil `.gitignore` zwar `.wav`, `.mp3`, `.flac` und `assets/**/*.mp3` abdeckt, aber keine explizite Regel fuer `local_assets/music/` und keine Endungen `.m4a`, `.aac`, `.ogg`, `.opus`.
- Spaeter sollte `.gitignore` gezielt erweitert werden, bevor ein lokaler Musikordner genutzt wird.
- Fuer Phase 5.5 sollte ein lokaler Ordner ausserhalb des Git-Commit-Scope genutzt werden.

## Empfehlung fuer spaetere Struktur

Empfohlene lokale Struktur:

```text
local_assets/music/
  intro/
  background/
  peak/
  outro/
```

Wichtig:
- `local_assets/music/` soll spaeter nicht committed werden.
- Musikdateien nur lokal.
- Nur Owner-freigegebene oder lizenzklare Musik.
- Keine automatischen Downloads.

## Next

Naechster Schritt:
Phase 5.5-2 Musik-Contracts / Manifest + Safety-Flags

Nur nach Master-GO.
