from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.render_versioning import (
    next_render_version,
    render_filename,
    versioned_final_path,
)


def test_render_versioning_smoke() -> None:
    job_id = "job_render_versioning_smoke"

    with TemporaryDirectory() as temp_dir:
        export_dir = Path(temp_dir)

        empty_next_version = next_render_version(export_dir, job_id)
        generated_filename = render_filename(job_id, empty_next_version)
        assert empty_next_version == 1
        assert generated_filename == f"{job_id}_v1_final.mp4"
        assert versioned_final_path(export_dir, job_id, 1).name == generated_filename

        (export_dir / generated_filename).write_bytes(b"fake mp4 v1")
        after_v1_next_version = next_render_version(export_dir, job_id)
        assert after_v1_next_version == 2

        (export_dir / render_filename(job_id, 2)).write_bytes(b"fake mp4 v2")
        after_v1_v2_next_version = next_render_version(export_dir, job_id)
        assert after_v1_v2_next_version == 3

        legacy_dir = export_dir / "legacy"
        legacy_dir.mkdir()
        (legacy_dir / f"{job_id}_final.mp4").write_bytes(b"legacy final")
        legacy_final_next_version = next_render_version(legacy_dir, job_id)
        assert legacy_final_next_version == 2

        unwanted_suffixes = {".json", ".jpg", ".jpeg", ".png", ".mp3", ".wav"}
        created_files = [
            path for path in export_dir.rglob("*")
            if path.is_file()
        ]
        assert created_files
        assert not any(path.suffix.lower() in unwanted_suffixes for path in created_files)

    print(f"empty_next_version={empty_next_version}")
    print(f"after_v1_next_version={after_v1_next_version}")
    print(f"after_v1_v2_next_version={after_v1_v2_next_version}")
    print(f"legacy_final_next_version={legacy_final_next_version}")
    print(f"generated_filename={generated_filename}")
    print("RENDER VERSIONING SMOKE TEST PASSED")


if __name__ == "__main__":
    test_render_versioning_smoke()
