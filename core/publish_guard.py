from __future__ import annotations

import os

from core.content_variant_repository import ContentVariantRepository
from core.publish_result_repository import PublishResultRepository
from models.publish_guard_result import PublishGuardResult
from models.publish_package import PublishPackage
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class PublishGuard:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
        content_variant_repository: ContentVariantRepository | None = None,
        publish_result_repository: PublishResultRepository | None = None,
        exports_base_path: str = "exports",
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.content_variant_repository = (
            content_variant_repository or ContentVariantRepository(self.storage)
        )
        self.publish_result_repository = (
            publish_result_repository or PublishResultRepository(self.storage)
        )
        self.exports_base_path = exports_base_path

    def _iter_export_paths(self) -> list[str]:
        export_paths: list[str] = []

        if not self.storage.exists(self.exports_base_path):
            return export_paths

        for channel_name in self.storage.list_dir(self.exports_base_path):
            channel_path = self.storage.join(self.exports_base_path, channel_name)

            if not self.storage.is_dir(channel_path):
                continue

            for job_folder in self.storage.list_dir(channel_path):
                export_path = self.storage.join(channel_path, job_folder)

                if self.storage.is_dir(export_path):
                    export_paths.append(export_path)

        return export_paths

    def load_all_variants(self) -> list:
        variants = []

        for export_path in self._iter_export_paths():
            variants.extend(
                self.content_variant_repository.load_variants(export_path)
            )

        return variants

    def load_all_publish_results(self) -> list:
        publish_results = []

        for export_path in self._iter_export_paths():
            for filename in self.storage.list_dir(export_path):
                lower_name = str(filename).lower()

                if (
                    lower_name.startswith("publish_results")
                    and lower_name.endswith(".json")
                ):
                    publish_results.extend(
                        self.publish_result_repository.load_results(
                            export_path,
                            results_filename=filename,
                        )
                    )

        return publish_results

    def evaluate_package(
        self,
        publish_package: PublishPackage,
    ) -> PublishGuardResult:
        all_variants = self.load_all_variants()
        all_publish_results = self.load_all_publish_results()

        published_results = [
            result
            for result in all_publish_results
            if result.publish_status == "published"
        ]

        variant_by_id = {
            variant.variant_id: variant
            for variant in all_variants
            if variant.variant_id
        }

        current_title = (publish_package.title or "").strip().lower()
        current_description = (publish_package.description or "").strip().lower()
        current_video_path = str(publish_package.video_path or "").strip().lower()

        for result in published_results:
            if (
                publish_package.variant_id
                and result.variant_id == publish_package.variant_id
                and result.platform == publish_package.platform
            ):
                return PublishGuardResult(
                    job_id=publish_package.job_id,
                    variant_id=publish_package.variant_id,
                    target_platform=publish_package.platform,
                    guard_status="block",
                    risk_flags=[
                        "duplicate_variant",
                        "recently_published_similar",
                    ],
                    guard_reason=(
                        "This exact variant was already published on the same platform"
                    ),
                    matched_reference_ids=[
                        value
                        for value in [result.variant_id, result.platform_video_id]
                        if value
                    ],
                    similarity_score=1.0,
                    requires_manual_review=False,
                )

        for result in published_results:
            if result.platform != publish_package.platform:
                continue

            reference_variant = (
                variant_by_id.get(result.variant_id)
                if result.variant_id
                else None
            )

            if reference_variant is None:
                continue

            if reference_variant.variant_id == publish_package.variant_id:
                continue

            ref_title = (reference_variant.title or "").strip().lower()
            ref_description = (reference_variant.description or "").strip().lower()
            ref_video_path = str(reference_variant.video_path or "").strip().lower()

            same_video = bool(current_video_path and ref_video_path == current_video_path)
            same_title = bool(current_title and ref_title == current_title)
            same_description = bool(
                current_description and ref_description == current_description
            )

            if same_video and (same_title or same_description):
                return PublishGuardResult(
                    job_id=publish_package.job_id,
                    variant_id=publish_package.variant_id,
                    target_platform=publish_package.platform,
                    guard_status="block",
                    risk_flags=["duplicate_assets"],
                    guard_reason=(
                        "A highly similar asset set was already published on this platform"
                    ),
                    matched_reference_ids=[
                        value
                        for value in [reference_variant.variant_id, result.platform_video_id]
                        if value
                    ],
                    similarity_score=0.95,
                    requires_manual_review=False,
                )

        for result in published_results:
            if result.platform == publish_package.platform:
                continue

            reference_variant = (
                variant_by_id.get(result.variant_id)
                if result.variant_id
                else None
            )

            if reference_variant is None:
                continue

            if reference_variant.variant_id == publish_package.variant_id:
                continue

            same_job = reference_variant.job_id == publish_package.job_id
            if not same_job:
                continue

            ref_title = (reference_variant.title or "").strip().lower()
            ref_description = (reference_variant.description or "").strip().lower()
            ref_video_path = str(reference_variant.video_path or "").strip().lower()

            same_video = bool(current_video_path and ref_video_path == current_video_path)
            same_title = bool(current_title and ref_title == current_title)
            same_description = bool(
                current_description and ref_description == current_description
            )
            same_packaging = (
                str(reference_variant.packaging_profile or "").strip().lower()
                == str(publish_package.packaging_profile or "").strip().lower()
            )

            if same_video and (same_title or same_description or same_packaging):
                return PublishGuardResult(
                    job_id=publish_package.job_id,
                    variant_id=publish_package.variant_id,
                    target_platform=publish_package.platform,
                    guard_status="warn",
                    risk_flags=[
                        "cross_platform_too_similar",
                        "low_originality",
                    ],
                    guard_reason=(
                        "This cross-platform publish candidate is very close to already "
                        "published material from the same job"
                    ),
                    matched_reference_ids=[
                        value
                        for value in [reference_variant.variant_id, result.platform_video_id]
                        if value
                    ],
                    similarity_score=0.85,
                    requires_manual_review=True,
                )

        return PublishGuardResult(
            job_id=publish_package.job_id,
            variant_id=publish_package.variant_id,
            target_platform=publish_package.platform,
            guard_status="allow",
            risk_flags=[],
            guard_reason="No material guard risks detected",
            matched_reference_ids=[],
            similarity_score=0.0,
            requires_manual_review=False,
        )

    def evaluate_packages(
        self,
        publish_packages: list[PublishPackage],
    ) -> list[PublishGuardResult]:
        if not publish_packages:
            raise ValueError("No publish packages provided")

        return [
            self.evaluate_package(publish_package)
            for publish_package in publish_packages
        ]