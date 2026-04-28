from models.job import Job
from models.publish_decision import PublishDecision
from models.validator_result import ValidatorResult
from shared.enums import AutopublishClass


class AutopublishGate:
    def decide(self, job: Job, validator_result: ValidatorResult) -> PublishDecision:
        if not validator_result.ready_for_publish:
            return PublishDecision(
                job_id=job.job_id,
                decision="blocked",
                reason="Validator failed",
            )

        if job.autopublish_class == AutopublishClass.MANUAL_ONLY:
            return PublishDecision(
                job_id=job.job_id,
                decision="approval_required",
                reason="Manual approval required for this job class",
            )

        if job.autopublish_class in {
            AutopublishClass.CONDITIONAL,
            AutopublishClass.SAFE_AUTO,
        }:
            return PublishDecision(
                job_id=job.job_id,
                decision="autopublish_allowed",
                reason="Validator passed and job class allows publish flow",
            )

        return PublishDecision(
            job_id=job.job_id,
            decision="blocked",
            reason="Unknown autopublish class",
        )