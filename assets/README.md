# Zenith Asset-Struktur

Dieser Ordner enthält nur kleine, versionierbare Struktur- und Manifest-Dateien.
Große Medien-Dateien wie Musik, Videos, Bilder und Rohmaterial gehören nicht in Git.

## Ordner

- `music/`: Musik-Dateien für spätere Schnitt- und Upload-Workflows.
- `sfx/`: Soundeffekte.
- `sfx/censor/`: Zensur-Soundeffekte und das bestehende `censor_sfx_manifest.json`.
- `voice_profile/`: Stimmprofil-Referenzen für spätere Audio-/Voice-Features.
- `thumbnail_faces/`: Gesichtsvorlagen für spätere Thumbnail-Workflows.
- `thumbnail_references/`: Thumbnail-Referenzen und Stilbeispiele.
- `intro_outro_material/`: Intro-/Outro-Material.
- `channel_assets/`: Kanalbezogene Assets.
- `style_references/`: Stilreferenzen für Schnitt, Branding und Packaging.

## Git-Regel

Die Ordnerstruktur, `.gitkeep`, diese README und `assets/sfx/censor/censor_sfx_manifest.json` werden getrackt.
Große Medien-Dateien werden über `.gitignore` ignoriert.
