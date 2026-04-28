from models.job import Job


class ContentClassifier:
    def classify(self, job: Job) -> str:
        # MVP Logik (später KI)

        file_name = job.raw_video_path.lower()

        if "react" in file_name or "reaction" in file_name:
            return "reaction"

        if "stream" in file_name or "live" in file_name:
            return "stream"

        return "stream"  # default fallback