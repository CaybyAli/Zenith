from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "assets/sfx/censor/censor_sfx_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_censor_sfx_folder_exists() -> None:
    assert (PROJECT_ROOT / "assets/sfx/censor").is_dir()


def test_censor_sfx_manifest_exists() -> None:
    assert MANIFEST_PATH.is_file()


def test_manifest_default_is_known_option() -> None:
    manifest = _manifest()

    assert manifest["default"] in {"quack", "dolphin", "beep"}


def test_manifest_contains_required_options() -> None:
    manifest = _manifest()

    assert {"quack", "dolphin", "beep"} <= set(manifest["options"])


def test_manifest_paths_stay_under_censor_sfx_folder() -> None:
    manifest = _manifest()

    for option in manifest["options"].values():
        assert str(option["path"]).startswith("assets/sfx/censor/")


def test_manifest_documents_p2_4_render_overlay_assets() -> None:
    notes = " ".join(_manifest().get("notes", []))

    assert "P2-4: Real WAV assets are committed and used by FinalRenderDriver." in notes
    assert "Censor SFX is mixed into rendered audio with FFmpeg amix normalize=0." in notes
    assert "Unknown replacement_sfx values fall back to the manifest default." in notes
    assert "Audio overlay is rendered in 2B-24.5." not in notes


def test_censor_sfx_manifest_has_no_bom_and_ends_with_newline() -> None:
    content = MANIFEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
