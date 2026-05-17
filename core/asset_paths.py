from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = PROJECT_ROOT / "assets"

MUSIC_DIR = ASSETS_ROOT / "music"
SFX_DIR = ASSETS_ROOT / "sfx"
CENSOR_SFX_DIR = SFX_DIR / "censor"
VOICE_PROFILE_DIR = ASSETS_ROOT / "voice_profile"
THUMBNAIL_FACES_DIR = ASSETS_ROOT / "thumbnail_faces"
THUMBNAIL_REFERENCES_DIR = ASSETS_ROOT / "thumbnail_references"
INTRO_OUTRO_MATERIAL_DIR = ASSETS_ROOT / "intro_outro_material"
CHANNEL_ASSETS_DIR = ASSETS_ROOT / "channel_assets"
STYLE_REFERENCES_DIR = ASSETS_ROOT / "style_references"

CENSOR_SFX_MANIFEST = CENSOR_SFX_DIR / "censor_sfx_manifest.json"

REQUIRED_ASSET_DIRS = {
    "assets": ASSETS_ROOT,
    "music": MUSIC_DIR,
    "sfx": SFX_DIR,
    "censor_sfx": CENSOR_SFX_DIR,
    "voice_profile": VOICE_PROFILE_DIR,
    "thumbnail_faces": THUMBNAIL_FACES_DIR,
    "thumbnail_references": THUMBNAIL_REFERENCES_DIR,
    "intro_outro_material": INTRO_OUTRO_MATERIAL_DIR,
    "channel_assets": CHANNEL_ASSETS_DIR,
    "style_references": STYLE_REFERENCES_DIR,
}


def asset_path(*parts: str) -> Path:
    return ASSETS_ROOT.joinpath(*parts)


def music_dir() -> Path:
    return MUSIC_DIR


def sfx_dir() -> Path:
    return SFX_DIR


def censor_sfx_dir() -> Path:
    return CENSOR_SFX_DIR


def voice_profile_dir() -> Path:
    return VOICE_PROFILE_DIR


def thumbnail_faces_dir() -> Path:
    return THUMBNAIL_FACES_DIR


def thumbnail_references_dir() -> Path:
    return THUMBNAIL_REFERENCES_DIR


def intro_outro_material_dir() -> Path:
    return INTRO_OUTRO_MATERIAL_DIR


def channel_assets_dir() -> Path:
    return CHANNEL_ASSETS_DIR


def style_references_dir() -> Path:
    return STYLE_REFERENCES_DIR


def verify_asset_structure() -> dict[str, bool]:
    return {
        name: path.exists() and path.is_dir()
        for name, path in REQUIRED_ASSET_DIRS.items()
    }
