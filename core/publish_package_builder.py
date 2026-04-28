from models.content_variant import ContentVariant
from models.publish_package import PublishPackage
from shared.enums import TargetFormat


class PublishPackageBuilder:
    def build_from_variant(
        self,
        variant: ContentVariant,
    ) -> PublishPackage:
        policy_snapshot = dict(variant.platform_policy_snapshot or {})

        resolved_source_video_path = (
            variant.source_video_path
            if variant.source_video_path
            else variant.video_path
        )

        return PublishPackage(
            job_id=variant.job_id,
            video_path=variant.video_path,
            source_video_path=resolved_source_video_path,
            title=variant.title,
            description=variant.description,
            hashtags=list(variant.hashtags),
            thumbnail_path=variant.thumbnail_or_cover_path,
            platform=variant.target_platform,
            channel_type=variant.channel_type,
            target_format=TargetFormat(
                str(policy_snapshot.get("target_format", "short"))
            ),
            requires_manual_approval=bool(
                policy_snapshot.get("requires_manual_approval", True)
            ),
            title_mode=str(policy_snapshot.get("title_mode", "standard")),
            description_mode=str(policy_snapshot.get("description_mode", "standard")),
            hashtags_mode=str(policy_snapshot.get("hashtags_mode", "standard")),
            subtitle_style=str(policy_snapshot.get("subtitle_style", "standard")),
            packaging_profile=str(policy_snapshot.get("packaging_profile", "standard")),
            length_profile=str(policy_snapshot.get("length_profile", "standard")),
            preferred_aspect_ratio=str(
                policy_snapshot.get("preferred_aspect_ratio", "16:9")
            ),
            thumbnail_required=bool(
                policy_snapshot.get("thumbnail_required", True)
            ),
            uploader_backend=policy_snapshot.get("uploader_backend"),
            variant_id=variant.variant_id,
        )

    def build(
        self,
        variants: list[ContentVariant],
    ) -> list[PublishPackage]:
        if not variants:
            raise ValueError("No content variants provided")

        return [
            self.build_from_variant(variant)
            for variant in variants
        ]