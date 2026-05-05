from __future__ import annotations

import re
from pathlib import Path


def render_filename(job_id: str, render_version: int) -> str:
    if render_version < 1:
        raise ValueError("render_version must be >= 1")
    return f"{job_id}_v{render_version}_final.mp4"


def next_render_version(export_dir: str | Path, job_id: str) -> int:
    export_path = Path(export_dir)
    version_pattern = re.compile(
        rf"^{re.escape(job_id)}_v(\d+)_final\.mp4$",
        re.IGNORECASE,
    )

    versions: list[int] = []
    if export_path.exists():
        for file_path in export_path.iterdir():
            match = version_pattern.match(file_path.name)
            if match:
                versions.append(int(match.group(1)))

    if versions:
        return max(versions) + 1

    legacy_final = export_path / f"{job_id}_final.mp4"
    if legacy_final.exists():
        return 2

    return 1


def versioned_final_path(export_dir: str | Path, job_id: str, render_version: int) -> Path:
    return Path(export_dir) / render_filename(job_id, render_version)
