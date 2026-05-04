from __future__ import annotations

from models.job import Job
from shared.channel_policies import get_channel_group, get_channel_policy
from shared.enums import ChannelType, JobStatus, JobType, PipelineType
from shared.errors import RoutingError


class RoutingEngine:
    def route(self, job: Job) -> Job:
        policy = get_channel_policy(job.channel_type.value)
        pipeline = self._resolve_pipeline(job)

        job.pipeline_type = pipeline
        job.status = JobStatus.ROUTED
        job.current_module = f"routing_engine:{policy.channel_group}"
        job.touch()
        return job

    def _resolve_pipeline(self, job: Job) -> PipelineType:
        if job.job_type == JobType.GAMING:
            if job.channel_type == ChannelType.VLOG_MAIN:
                return PipelineType.VLOG
            if job.channel_type not in {
                ChannelType.GAMING_MAIN, ChannelType.GAMING_UNCUT
            }:
                raise RoutingError(
                    f"Gaming job cannot use channel_type={job.channel_type}"
                )
            return PipelineType.GAMING

        if job.job_type == JobType.FACELESS:
            if job.channel_type != ChannelType.FACELESS_TREND:
                raise RoutingError(
                    f"Faceless job cannot use channel_type={job.channel_type}"
                )
            return PipelineType.FACELESS

        raise RoutingError(f"Unsupported job_type={job.job_type}")
