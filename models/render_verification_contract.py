from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RenderVerificationExpectedSpec:
    container: str | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    expected_duration_seconds: float | None = None
    duration_tolerance_seconds: float = 1.0
    require_video_stream: bool = True
    require_audio_stream: bool = True
    require_faststart: bool = True
    require_nonzero_size: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderVerificationCheck:
    check_id: str
    check_type: str
    description: str
    expected_value: Any = None
    actual_value: Any = None
    status: str = "planned"
    severity: str = "info"
    planned_only: bool = True
    can_run_now: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderVerificationProbePlan:
    probe_id: str
    tool: str = "ffprobe"
    path_hint: str | None = None
    argv_preview: list[str] = field(default_factory=list)
    target_path_hint: str | None = None
    smoke_probe_only: bool = False
    project_output_probe_allowed: bool = False
    can_execute_probe: bool = False
    can_probe_project_output: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderVerificationContractReport:
    report_id: str
    job_id: str
    status: str
    expected_spec: RenderVerificationExpectedSpec
    checks: list[RenderVerificationCheck]
    probe_plan: RenderVerificationProbePlan
    total_checks: int = 0
    planned_check_count: int = 0
    runnable_smoke_check_count: int = 0
    blocked_check_count: int = 0
    contract_only: bool = True
    dry_run_only: bool = True
    smoke_probe_allowed: bool = False
    project_output_probe_allowed: bool = False
    can_verify_smoke_output: bool = False
    can_verify_project_output: bool = False
    can_probe_media_files: bool = False
    can_render: bool = False
    can_write_media: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = "review_render_verification_contract"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
