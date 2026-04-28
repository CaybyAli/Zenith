from pathlib import Path

from models.job import Job
from models.thumbnail_package import ThumbnailPackage
from core.thumbnail_forge import ThumbnailForge
from core.thumbnail_prompt_builder import build_thumbnail_prompt


class AIThumbnailForge:
    def generate(self, job: Job, final_video_path: str) -> ThumbnailPackage:
        prompt = build_thumbnail_prompt(job)

        prompt_path = Path(final_video_path).with_suffix(".thumbnail_prompt.txt")
        prompt_path.write_text(prompt, encoding="utf-8")

        # Sichere Übergangsversion:
        # KI-Prompt wird bereits erzeugt und gespeichert,
        # Bild selbst fällt bis zur echten KI-Anbindung weiter auf Frame-Thumbnail zurück.
        return ThumbnailForge().generate(job, final_video_path)