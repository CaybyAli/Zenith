from pathlib import Path
import sys

from core.existing_longform_shorts_stage import run_shorts_from_existing_longform_output
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)

source = Path(sys.argv[1])
job = Job(
    job_id="job_p5_g2_real_caption_shorts",
    job_type=JobType.GAMING,
    channel_type=ChannelType.GAMING_MAIN,
    target_format=TargetFormat.SHORT,
    target_platforms=["youtube"],
    status=JobStatus.RENDERED,
    mode=Mode.NORMAL,
    autopublish_class=AutopublishClass.MANUAL_ONLY,
    confidence_score=0.0,
    validator_status=ValidatorStatus.NOT_VALIDATED,
)

result = run_shorts_from_existing_longform_output(
    job=job,
    source_video_path=source,
    output_base_dir=Path("exports") / "gaming_main",
    power_profile="performance",
    add_captions=True,
)

print("P5_G2_REAL_SHORTS_RESULT", result)
for clip in job.shorts_clips:
    print(
        "P5_G2_SHORT",
        "index=", clip.clip_index,
        "status=", clip.status,
        "path=", clip.output_path,
    )
