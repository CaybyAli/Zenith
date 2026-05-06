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
        checks = []

        def add_check(name: str, passed: bool, detail: str) -> None:
            checks.append(
                {
                    "name": name,
                    "passed": bool(passed),
                    "detail": str(detail),
                }
            )

        if not final_video_path:
            blocking_issues.append("Missing final video")
            add_check("final_video", False, "Missing final video")
        else:
            add_check("final_video", True, str(final_video_path))

        if not title_package.primary_title:
            blocking_issues.append("Missing title")
            add_check("title", False, "Missing title")
        else:
            add_check("title", True, title_package.primary_title)

        if not metadata.description:
            blocking_issues.append("Missing description")
            add_check("description", False, "Missing description")
        else:
            add_check("description", True, "description present")

        if thumbnail_package is None or not thumbnail_package.selected_thumbnail:
            blocking_issues.append("Missing thumbnail")
            add_check("thumbnail", False, "Missing thumbnail")
        elif not os.path.exists(thumbnail_package.selected_thumbnail):
            blocking_issues.append("Thumbnail file not found")
            add_check("thumbnail", False, f"Thumbnail file not found: {thumbnail_package.selected_thumbnail}")
        else:
            add_check("thumbnail", True, thumbnail_package.selected_thumbnail)

        if len(title_package.primary_title) < 5:
            warnings.append("Title is very short")
            add_check("title_length", False, "Title is very short")
        else:
            add_check("title_length", True, "title length ok")

        ready_for_publish = len(blocking_issues) == 0
        status = "passed" if ready_for_publish else "failed"
        reason = "; ".join(blocking_issues) if blocking_issues else "all blocking checks passed"

        return ValidatorResult(
            job_id=job.job_id,
            validator_status=status,
            blocking_issues=blocking_issues,
            warnings=warnings,
            ready_for_publish=ready_for_publish,
            reason=reason,
            details={
                "checks": checks,
                "blocking_issue_count": len(blocking_issues),
                "warning_count": len(warnings),
            },
        )
