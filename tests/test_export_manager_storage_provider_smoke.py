from pathlib import Path
import shutil

from core.export_manager import ExportManager
from shared.enums import ChannelType
from storage.local_storage_provider import LocalStorageProvider


class DummyPackage:
    def __init__(self, video_path: str, thumbnail_path: str) -> None:
        self.job_id = "job_export_storage_smoke_001"
        self.channel_type = ChannelType.GAMING_MAIN
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.title = "Export Storage Test"
        self.description = "Export manager storage abstraction smoke test"
        self.hashtags = ["#zenith", "#test"]


def main() -> None:
    source_dir = Path("tmp/export_manager_storage_test")
    export_dir = Path("exports/gaming_main/job_export_storage_smoke_001")

    if source_dir.exists():
        shutil.rmtree(source_dir)
    if export_dir.exists():
        shutil.rmtree(export_dir)

    source_dir.mkdir(parents=True, exist_ok=True)

    video_file = source_dir / "video_source.mp4"
    thumbnail_file = source_dir / "thumbnail_source.jpg"

    video_file.write_bytes(b"fake-video")
    thumbnail_file.write_bytes(b"fake-thumbnail")

    package = DummyPackage(
        video_path=str(video_file),
        thumbnail_path=str(thumbnail_file),
    )

    manager = ExportManager(storage_provider=LocalStorageProvider())
    export_path = manager.export(package)

    exported_video = Path(export_path) / "video.mp4"
    exported_thumbnail = Path(export_path) / "thumbnail.jpg"
    metadata_file = Path(export_path) / "metadata.json"

    assert exported_video.exists()
    assert exported_thumbnail.exists()
    assert metadata_file.exists()

    content = metadata_file.read_text(encoding="utf-8")
    assert '"title": "Export Storage Test"' in content
    assert '"description": "Export manager storage abstraction smoke test"' in content

    print("EXPORT MANAGER STORAGE PROVIDER SMOKE TEST PASSED")
    print({"export_path": export_path})

    if source_dir.exists():
        shutil.rmtree(source_dir)
    if export_dir.exists():
        shutil.rmtree(export_dir)


if __name__ == "__main__":
    main()