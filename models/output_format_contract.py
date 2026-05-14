from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class OutputVideoSpec:
    codec: str = "h264"
    encoder_intent: str = "libx264"
    resolution_width: int = 1920
    resolution_height: int = 1080
    fps: int = 60
    crf: int = 18
    preset: str = "fast"
    pix_fmt: str = "yuv420p"
    use_nvenc_if_available: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputAudioSpec:
    codec: str = "aac"
    bitrate_kbps: int = 320
    target_lufs: float = -14.0
    true_peak_db: float = -1.0
    loudnorm_required: bool = True
    sample_rate: int = 48000
    channels: int = 2
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputContainerSpec:
    container: str = "mp4"
    extension: str = ".mp4"
    faststart: bool = True
    movflags: str = "+faststart"
    compatible: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputFormatPreset:
    preset_id: str
    profile: str
    platform: str
    target_format: str
    video: OutputVideoSpec
    audio: OutputAudioSpec
    container: OutputContainerSpec
    filename_hint: str = ""
    output_path_hint: str = ""
    safe_filename_hint: str = ""
    compatible_with_capabilities: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputFormatContractReport:
    report_id: str
    job_id: str
    status: str
    preset: OutputFormatPreset
    available_presets: list[str]
    selected_profile: str
    selected_platform: str
    selected_target_format: str
    can_prepare_output_format: bool
    can_render: bool = False
    can_write_project_output: bool = False
    can_process_user_media: bool = False
    can_execute_ffmpeg: bool = False
    dry_run_only: bool = True
    contract_only: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = "review_output_format_contract"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
