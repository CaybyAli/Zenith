# Phase 5.5 Music Library Rules

## Grundregel

Musik darf nur verwendet werden, wenn sie lokal vorhanden und vom Owner bewusst freigegeben ist.
Musik darf Ali/Friend-Stimmen niemals ueberdecken.

## Erlaubt spaeter

- lokale Musikdateien
- Owner-freigegebene Musik
- lizenzklare Musik
- klare Kategorien:
  - intro
  - outro
  - vlog_background
  - funny_gaming_background
  - fail
  - hype
  - sad
- `hype` bedeutet spannend / Action / Peak / Clutch
- `suspense` ist kein echter Ordner mehr, sondern nur Mood-Alias zu `hype`

Empfohlene lokale Struktur spaeter:
- `local_assets/music/main_account/intro/`
- `local_assets/music/main_account/outro/`
- `local_assets/music/main_account/vlog_background/`
- `local_assets/music/main_account/funny_gaming_background/`
- `local_assets/music/main_account/fail/`
- `local_assets/music/main_account/hype/`
- `local_assets/music/main_account/sad/`

Vorbereitet fuer manuelles Einsortieren durch Ali:
- `local_assets/music/main_account/intro/`
- `local_assets/music/main_account/outro/`
- `local_assets/music/main_account/vlog_background/`
- `local_assets/music/main_account/funny_gaming_background/`
- `local_assets/music/main_account/fail/`
- `local_assets/music/main_account/hype/`
- `local_assets/music/main_account/sad/`

Ali hat diese Ordner manuell mit Epidemic-Sound-Musik gefuellt. Musikdateien bleiben lokal und werden nicht committed.
Das Preview Gate darf keine Musikdateien committen und darf Musikdateien nicht lesen, oeffnen, kopieren, loeschen oder konvertieren.

Deprecated alte Ordner, falls lokal vorhanden:
- `local_assets/music/main_account/funny/`
- `local_assets/music/main_account/suspense/`
- `local_assets/music/main_account/calm/`
- `local_assets/music/main_account/victory/`
- `local_assets/music/main_account/emotional/`
- `local_assets/music/main_account/background/`
- `local_assets/music/main_account/peak/`

Deprecated Ordner werden nicht automatisch geloescht, verschoben oder bereinigt.

## Verboten

- automatische Downloads
- externe Musikdienste
- API-Keys
- unklare Lizenzen
- copyrighted Musik automatisch einfuegen
- Musikdateien in Git committen
- Musik ohne Manifest verwenden
- Musik ohne Owner Review finalisieren
- Uncut-Musikordner anlegen oder verwenden
- Musik fuer Uncut auswaehlen

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

Verifikation nach 5.5-4B:
- `local_assets/music/` ist ignored.
- `git ls-files local_assets/music` ist leer.
- Musikdateien tracked: nein.
- Musikdateien staged: nein.
- Anzahl lokal gepruefter Musikdateien: 87.
- Dateitypen: 87 x `.mp3`.
- `local_assets/music/uncut/` existiert nicht.
- Musikdateien wurden nicht geoeffnet, gelesen, abgespielt, konvertiert oder gerendert.

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
- Channel: nur `main`

## Mapping-Aliasse

- `funny` -> `funny_gaming_background`
- `suspense` -> `hype`
- `hype` -> `hype`
- `sad` -> `sad`
- `fail` -> `fail`
- `calm`, `neutral`, default gameplay -> `vlog_background`
- `intro` / `outro` -> `intro` / `outro`
- Uncut -> `music_allowed=false`, `category=none`

## Uncut-Regel

Uncut bleibt original/naturbelassen und bekommt keine Musik. Es werden keine Uncut-Musikordner verwendet.
`local_assets/music/uncut/` wird nicht erstellt.

## Selector-Regel

- Selector nutzt nur Metadaten.
- Selector ist Main Account only.
- Uncut wird blockiert.
- Missing Category darf nicht heimlich fallbacken.
- Selector darf keine Musikdateien lesen, kopieren, einfuegen oder final fuer echte Videos aktivieren.

## Naechster Gate

- 5.5-7 Final Audit oder kontrollierter Preview-Run nur nach Master-GO.
- Weiterhin kein Musik-Build ohne eigenes Master-GO.
- Weiterhin kein echter Audio-Mix ohne eigenes Master-GO.
- Musik bleibt lokal und ignored.
- Preview Gate darf keine Musikdateien committen.
