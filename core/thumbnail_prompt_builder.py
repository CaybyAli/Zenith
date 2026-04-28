from models.job import Job


def build_thumbnail_prompt(job: Job) -> str:
    if getattr(job, "title", None) and str(job.title).strip():
        title = str(job.title).strip()
    elif getattr(job, "topic", None) and str(job.topic).strip():
        title = str(job.topic).strip()
    else:
        title = "Gaming Highlight"

    channel = str(job.channel_type.value).replace("_", " ")

    return (
        f"YouTube gaming thumbnail, high contrast, cinematic lighting, "
        f"clear focal subject, expressive action moment, bold composition, "
        f"clean background separation, premium creator style, no watermarks, "
        f"no extra text, theme: {title}, channel: {channel}"
    )