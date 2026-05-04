import os

from models.job import Job
from models.metadata_package import MetadataPackage
from models.thumbnail_package import ThumbnailPackage
from models.title_package import TitlePackage
from models.validator_result import ValidatorResult


class Validator:
    def validate(
        self,
        job: Job,
        final_video_path: str,
        title_package: TitlePackage,
        metadata: MetadataPackage,
        thumbnail_package: ThumbnailPackage,
    ) -> ValidatorResult:
        blocking_issues = []
        warnings = []

        if not final_video_path:
            blocking_issues.append("Missing final video")

        if not title_package.primary_title:
            blocking_issues.append("Missing title")

        if not metadata.description:
            blocking_issues.append("Missing description")

        if thumbnail_package is None or not thumbnail_package.selected_thumbnail:
            blocking_issues.append("Missing thumbnail")
        elif not os.path.exists(thumbnail_package.selected_thumbnail):
            blocking_issues.append("Thumbnail file not found")

        if len(title_package.primary_title) < 5:
            warnings.append("Title is very short")

        ready_for_publish = len(blocking_issues) == 0
        status = "passed" if ready_for_publish else "failed"

        return ValidatorResult(
            job_id=job.job_id,
            validator_status=status,
            blocking_issues=blocking_issues,
            warnings=warnings,
            ready_for_publish=ready_for_publish,
        )