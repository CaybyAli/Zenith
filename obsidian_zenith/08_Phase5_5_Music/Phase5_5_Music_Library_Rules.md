# Phase 5.5 Music Library Rules

## Grundregel

Musik darf nur verwendet werden, wenn sie lokal vorhanden und vom Owner bewusst freigegeben ist.

## Erlaubt spaeter

- lokale Musikdateien
- Owner-freigegebene Musik
- lizenzklare Musik
- klare Kategorien:
  - intro
  - background
  - peak
  - outro

## Verboten

- automatische Downloads
- externe Musikdienste
- API-Keys
- unklare Lizenzen
- copyrighted Musik automatisch einfuegen
- Musikdateien in Git committen
- Musik ohne Manifest verwenden
- Musik ohne Owner Review finalisieren

## Git-Regel

Musikdateien sollen spaeter lokal bleiben und nicht in Git landen.

Empfehlung:
- `local_assets/music/` spaeter gitignore-geschuetzt fuehren
- keine Musikdateien committen
- nur Metadaten/Manifeste als Reports erzeugen
- Reports bleiben untracked, ausser Master erlaubt es

Aktueller Schutz nach 5.5-2:
- `local_assets/music/`
- `*.m4a`
- `*.aac`
- `*.ogg`
- `*.opus`
- bestehend: `*.wav`, `*.mp3`, `*.flac`, `assets/**/*.wav`, `assets/**/*.mp3`

## Pflicht-Metadaten spaeter

Fuer jede Musikdatei spaeter dokumentieren:
- Dateiname
- Kategorie
- Quelle
- Owner-Freigabe
- Lizenzstatus
- Dauer
- Lautstaerkepruefung
- Einsatzbereich
