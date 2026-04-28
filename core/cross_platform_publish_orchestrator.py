from __future__ import annotations

from core.publish_guard import PublishGuard
from core.publish_guard_repository import PublishGuardRepository
from core.publish_result_repository import PublishResultRepository
from core.publisher import Publisher
from models.publish_decision import PublishDecision
from models.publish_guard_result import PublishGuardResult
from models.publish_package import PublishPackage
from models.publish_result import PublishResult


class CrossPlatformPublishOrchestrator:
    def __init__(
        self,
        publisher: Publisher | None = None,
        publish_result_repository: PublishResultRepository | None = None,
        publish_guard: PublishGuard | None = None,
        publish_guard_repository: PublishGuardRepository | None = None,
    ) -> None:
        self.publisher = publisher or Publisher()
        self.publish_result_repository = (
            publish_result_repository or PublishResultRepository()
        )
        self.publish_guard = publish_guard or PublishGuard()
        self.publish_guard_repository = (
            publish_guard_repository or PublishGuardRepository()
        )

    def _build_blocked_result(
        self,
        publish_package: PublishPackage,
        guard_result: PublishGuardResult,
    ) -> PublishResult:
        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="blocked",
            message=(
                f"Publish blocked by guard for {publish_package.platform.value}: "
                f"{guard_result.guard_reason}"
            ),
            variant_id=publish_package.variant_id,
            backend_name=publish_package.uploader_backend,
            error_message=guard_result.guard_reason,
        )

    def _build_guard_review_result(
        self,
        publish_package: PublishPackage,
        guard_result: PublishGuardResult,
    ) -> PublishResult:
        return PublishResult(
            job_id=publish_package.job_id,
            platform=publish_package.platform,
            publish_status="queued_for_approval",
            message=(
                f"Publish warned by guard for {publish_package.platform.value}: "
                f"{guard_result.guard_reason}"
            ),
            variant_id=publish_package.variant_id,
            backend_name=publish_package.uploader_backend,
            error_message=guard_result.guard_reason,
        )

    def execute(
        self,
        publish_packages: list[PublishPackage],
        publish_decision: PublishDecision,
        export_path: str | None = None,
        results_filename: str = "publish_results.json",
        guard_results_filename: str = "publish_guard_results.json",
    ) -> list[PublishResult]:
        if not publish_packages:
            raise ValueError("No publish packages provided")

        guard_results = self.publish_guard.evaluate_packages(publish_packages)

        if export_path:
            self.publish_guard_repository.save_results(
                export_path=export_path,
                guard_results=guard_results,
                results_filename=guard_results_filename,
            )

        publish_results: list[PublishResult] = []

        for publish_package, guard_result in zip(publish_packages, guard_results):
            if guard_result.guard_status == "block":
                publish_results.append(
                    self._build_blocked_result(
                        publish_package=publish_package,
                        guard_result=guard_result,
                    )
                )
                continue

            if (
                guard_result.guard_status == "warn"
                and guard_result.requires_manual_review
            ):
                publish_results.append(
                    self._build_guard_review_result(
                        publish_package=publish_package,
                        guard_result=guard_result,
                    )
                )
                continue

            publish_result = self.publisher.publish(
                publish_package,
                publish_decision,
            )
            publish_results.append(publish_result)

        if export_path:
            self.publish_result_repository.save_results(
                export_path=export_path,
                publish_results=publish_results,
                results_filename=results_filename,
            )

        return publish_results