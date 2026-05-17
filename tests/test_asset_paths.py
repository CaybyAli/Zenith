from pathlib import Path

from core.asset_paths import (
    ASSETS_ROOT,
    CENSOR_SFX_MANIFEST,
    asset_path,
    channel_assets_dir,
    censor_sfx_dir,
    intro_outro_material_dir,
    music_dir,
    sfx_dir,
    style_references_dir,
    thumbnail_faces_dir,
    thumbnail_references_dir,
    verify_asset_structure,
    voice_profile_dir,
)


def test_asset_root_exists():
    assert ASSETS_ROOT.exists()
    assert ASSETS_ROOT.is_dir()


def test_asset_helper_paths_exist():
    paths = [
        music_dir(),
        sfx_dir(),
        censor_sfx_dir(),
        voice_profile_dir(),
        thumbnail_faces_dir(),
        thumbnail_references_dir(),
        intro_outro_material_dir(),
        channel_assets_dir(),
        style_references_dir(),
    ]

    for path in paths:
        assert isinstance(path, Path)
        assert path.exists()
        assert path.is_dir()


def test_asset_path_joins_under_assets_root():
    assert asset_path("sfx", "censor") == censor_sfx_dir()


def test_verify_asset_structure_reports_complete():
    report = verify_asset_structure()

    assert report
    assert all(report.values())


def test_existing_censor_sfx_manifest_is_kept_trackable():
    assert CENSOR_SFX_MANIFEST.exists()
    assert CENSOR_SFX_MANIFEST.name == "censor_sfx_manifest.json"
