from pathlib import Path

from shared.channel_policies import get_enabled_channel_types


class InboxScanner:
    def scan(self):
        jobs = []

        for channel_type in get_enabled_channel_types():
            channel_folder = Path("inbox") / channel_type

            if not channel_folder.exists() or not channel_folder.is_dir():
                continue

            for file in channel_folder.glob("*.mp4"):
                jobs.append({
                    "type": channel_type,
                    "path": str(file)
                })

        return jobs