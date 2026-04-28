from datetime import datetime, timezone

from core.youtube_uploader import YouTubeUploader
from models.publish_decision import PublishDecision
from models.publish_package import PublishPackage
from models.publish_result import PublishResult


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Publisher:
    def publish(
        self,
        publish_package: PublishPackage,
        publish_decision: PublishDecision,
    ) -> PublishResult:
        publish_target = (
            f"short:{publish_package.short_id}"
            if publish_package.short_id
            else "main_video"
        )

        print(
            "[DEBUG Publisher.publish]",
            publish_package.channel_type,
            publish_package.platform.value,
            publish_decision.decision,
            publish_target,
        )

        if publish_decision.decision == "approval_required":
            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="queued_for_approval",
                message=(
                    f"{publish_target} is ready for {publish_package.platform.value} "
                    f"and waiting for manual approval"
                ),
                variant_id=publish_package.variant_id,
                backend_name=publish_package.uploader_backend,
                error_message=None,
            )

        if publish_decision.decision == "autopublish_allowed":
            if publish_package.requires_manual_approval:
                return PublishResult(
                    job_id=publish_package.job_id,
                    platform=publish_package.platform,
                    publish_status="queued_for_approval",
                    message=(
                        f"{publish_target} is ready for {publish_package.platform.value} "
                        f"but platform policy requires manual approval"
                    ),
                    variant_id=publish_package.variant_id,
                    backend_name=publish_package.uploader_backend,
                    error_message=None,
                )

            if publish_package.uploader_backend == "youtube":
                uploader = YouTubeUploader(publish_package.channel_type.value)
                video_id = uploader.upload(publish_package)
                public_url = f"https://youtube.com/watch?v={video_id}"
                published_at = utc_now_iso()

                return PublishResult(
                    job_id=publish_package.job_id,
                    platform=publish_package.platform,
                    publish_status="published",
                    message=(
                        f"{publish_target} was uploaded to "
                        f"{publish_package.platform.value}"
                    ),
                    platform_video_id=video_id,
                    variant_id=publish_package.variant_id,
                    backend_name="youtube",
                    public_url=public_url,
                    error_message=None,
                    published_at=published_at,
                )

            if publish_package.uploader_backend == "tiktok":
                from core.tiktok_uploader import TikTokUploadError, TikTokUploader
                from shared.errors import ValidationError

                try:
                    video_id = TikTokUploader().upload(publish_package)
                    public_url = f"https://www.tiktok.com/video/{video_id}"
                    published_at = utc_now_iso()

                    return PublishResult(
                        job_id=publish_package.job_id,
                        platform=publish_package.platform,
                        publish_status="published",
                        message=(
                            f"{publish_target} was uploaded to "
                            f"{publish_package.platform.value}"
                        ),
                        platform_video_id=video_id,
                        variant_id=publish_package.variant_id,
                        backend_name="tiktok",
                        public_url=public_url,
                        error_message=None,
                        published_at=published_at,
                    )
                except (ValidationError, TikTokUploadError) as exc:
                    return PublishResult(
                        job_id=publish_package.job_id,
                        platform=publish_package.platform,
                        publish_status="failed",
                        message=f"{publish_target} TikTok upload failed",
                        variant_id=publish_package.variant_id,
                        backend_name="tiktok",
                        error_message=str(exc),
                    )

            return PublishResult(
                job_id=publish_package.job_id,
                platform=publish_package.platform,
                publish_status="unsupported_backend",
                message=(
                    f"{publish_target} is policy-resolved for "
                    f"{publish_package.platform.value}, but no uploader backend "
                    f"is implemented"
                ),
                variant_id=publish_package.variant_id,
                backend_name=publish_package.uploader_backend,
                error_message="No uploader backend implemented for platform",
            )

        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="blocked",
            message=(
                f"{publish_target} could not be published to "
                f"{publish_package.platform.value}"
            ),
            variant_id=publish_package.variant_id,
            backend_name=publish_package.uploader_backend,
            error_message="Publish decision blocked execution",
        )