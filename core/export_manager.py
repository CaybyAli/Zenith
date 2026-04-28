from __future__ import annotations

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class ExportManager:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def export(self, package):
        job_id = package.job_id
        channel_type = package.channel_type.value

        export_path = self.storage.join("exports", channel_type, job_id)
        self.storage.ensure_dir(export_path)

        if self.storage.exists(package.video_path):
            video_target = self.storage.join(export_path, "video.mp4")
            self.storage.copy_file(package.video_path, video_target)

        if package.thumbnail_path and self.storage.exists(package.thumbnail_path):
            thumbnail_target = self.storage.join(export_path, "thumbnail.jpg")
            self.storage.copy_file(package.thumbnail_path, thumbnail_target)
        else:
            print(f"[ExportManager] Thumbnail not found, skipping: {package.thumbnail_path}")

        metadata = {
            "title": package.title,
            "description": package.description,
            "hashtags": package.hashtags,
            "thumbnail_path": package.thumbnail_path,
        }

        metadata_file = self.storage.join(export_path, "metadata.json")
        self.storage.write_json(metadata_file, metadata, indent=2)

        print(f"[ExportManager] Exported job to {export_path}")
        return export_path