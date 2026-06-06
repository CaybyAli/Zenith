from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping


ALLOWED_CATEGORIES = ("intro", "background", "peak", "outro")
ALLOWED_LOCAL_ROOTS = (
    "local_assets/music",
    "assets/audio/gaming_main/music",
    "assets/music",
)
ALLOWED_LICENSE_STATUS = ("owner_approved", "royalty_free", "self_created")
FORBIDDEN_LICENSE_STATUS = ("unknown", "copyrighted_unknown", "missing")

SAFE_DEFAULT_FLAGS = {
    "music_build_started": False,
    "music_inserted": False,
    "render_used": False,
    "preview_render_used": False,
    "ingest_used": False,
    "qwen_used": False,
    "qwen_autocut_used": False,
    "runtime_learning_started": False,
    "phase_5_5_used": True,
    "external_download_used": False,
    "api_key_used": False,
    "music_files_committed": False,
    "production_files_modified": False,
    "deleted_files": [],
}


class MusicContractError(ValueError):
    pass


@dataclass(frozen=True)
class MusicItem:
    file_path: str
    category: str
    source: str
    owner_approved: bool
    license_status: str
    intended_use: str


def _as_repo_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve()


def _looks_like_windows_absolute(path_text: str) -> bool:
    return PureWindowsPath(path_text).is_absolute()


def _has_parent_escape(path_text: str) -> bool:
    parts = path_text.replace("\\", "/").split("/")
    return ".." in parts


def _to_repo_relative(repo_root: Path, path: str | Path) -> Path:
    path_text = str(path).strip()
    if not path_text:
        raise MusicContractError("file_path is required")
    if _has_parent_escape(path_text):
        raise MusicContractError("path parent traversal is not allowed")
    if _looks_like_windows_absolute(path_text):
        candidate = Path(path_text).resolve()
        try:
            return candidate.relative_to(repo_root)
        except ValueError as exc:
            raise MusicContractError("absolute path must stay inside repo root") from exc
    candidate = Path(path_text)
    if candidate.is_absolute():
        candidate = candidate.resolve()
        try:
            return candidate.relative_to(repo_root)
        except ValueError as exc:
            raise MusicContractError("absolute path must stay inside repo root") from exc
    return Path(path_text.replace("\\", "/"))


def normalize_music_path(repo_root: str | Path, path: str | Path) -> str:
    root = _as_repo_root(repo_root)
    relative_path = _to_repo_relative(root, path)
    return relative_path.as_posix().strip("/")


def validate_music_path(repo_root: str | Path, path: str | Path) -> str:
    normalized = normalize_music_path(repo_root, path)
    allowed = any(
        normalized == allowed_root or normalized.startswith(f"{allowed_root}/")
        for allowed_root in ALLOWED_LOCAL_ROOTS
    )
    if not allowed:
        raise MusicContractError(f"path is outside allowed music roots: {normalized}")
    return normalized


def _coerce_music_item(item: MusicItem | Mapping[str, Any]) -> MusicItem:
    if isinstance(item, MusicItem):
        return item
    missing = [
        field
        for field in (
            "file_path",
            "category",
            "source",
            "owner_approved",
            "license_status",
            "intended_use",
        )
        if field not in item
    ]
    if missing:
        raise MusicContractError(f"missing music metadata: {', '.join(missing)}")
    return MusicItem(
        file_path=str(item["file_path"]),
        category=str(item["category"]),
        source=str(item["source"]),
        owner_approved=bool(item["owner_approved"]),
        license_status=str(item["license_status"]),
        intended_use=str(item["intended_use"]),
    )


def validate_music_item(item: MusicItem | Mapping[str, Any], repo_root: str | Path) -> dict[str, Any]:
    music_item = _coerce_music_item(item)
    if music_item.category not in ALLOWED_CATEGORIES:
        raise MusicContractError(f"category is not allowed: {music_item.category}")
    if not music_item.owner_approved:
        raise MusicContractError("owner approval is required")
    if music_item.license_status in FORBIDDEN_LICENSE_STATUS:
        raise MusicContractError(f"license status is forbidden: {music_item.license_status}")
    if music_item.license_status not in ALLOWED_LICENSE_STATUS:
        raise MusicContractError(f"license status is not allowed: {music_item.license_status}")
    if not music_item.source.strip():
        raise MusicContractError("source is required")
    if not music_item.intended_use.strip():
        raise MusicContractError("intended_use is required")
    normalized_path = validate_music_path(repo_root, music_item.file_path)
    return {
        "file_path": normalized_path,
        "category": music_item.category,
        "source": music_item.source,
        "owner_approved": music_item.owner_approved,
        "license_status": music_item.license_status,
        "intended_use": music_item.intended_use,
    }


def build_empty_music_contract_manifest(repo_root: str | Path) -> dict[str, Any]:
    _as_repo_root(repo_root)
    return {
        "status": "ok",
        "phase": "Phase 5.5",
        "step": "5.5-2",
        "mode": "music_contracts_only",
        "phase_5_done": True,
        "p5_l_closed": True,
        "runtime_learning_locked": True,
        **SAFE_DEFAULT_FLAGS,
        "allowed_categories": list(ALLOWED_CATEGORIES),
        "allowed_roots": list(ALLOWED_LOCAL_ROOTS),
        "requires_owner_approval": True,
        "requires_license_clear": True,
        "writes_only_under": "reports/phase5_5_music_contracts",
        "next_step": "5.5-3 Energy-to-Music Mapping",
        "music_items": [],
        "warnings": [],
    }


def validate_music_contract_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    for flag_name, expected_value in SAFE_DEFAULT_FLAGS.items():
        if manifest.get(flag_name) != expected_value:
            raise MusicContractError(f"unsafe manifest flag: {flag_name}")
    if manifest.get("allowed_categories") != list(ALLOWED_CATEGORIES):
        raise MusicContractError("allowed categories do not match contract")
    if manifest.get("allowed_roots") != list(ALLOWED_LOCAL_ROOTS):
        raise MusicContractError("allowed roots do not match contract")
    if manifest.get("requires_owner_approval") is not True:
        raise MusicContractError("owner approval must be required")
    if manifest.get("requires_license_clear") is not True:
        raise MusicContractError("license clarity must be required")
    if manifest.get("writes_only_under") != "reports/phase5_5_music_contracts":
        raise MusicContractError("manifest output scope is invalid")
    if manifest.get("mode") != "music_contracts_only":
        raise MusicContractError("manifest mode is invalid")
    if manifest.get("runtime_learning_locked") is not True:
        raise MusicContractError("runtime learning must stay locked")
    if manifest.get("music_items") not in ([], None):
        raise MusicContractError("5.5-2 manifest must not select music items")
    if not isinstance(manifest.get("warnings", []), list):
        raise MusicContractError("warnings must be a list")
    return dict(manifest)
