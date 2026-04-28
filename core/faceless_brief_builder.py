from models.faceless_brief import FacelessBrief
from models.job import Job
from shared.errors import ValidationError


class FacelessBriefBuilder:
    def build(self, job: Job) -> FacelessBrief:
        if not job.topic:
            raise ValidationError("Faceless job needs a topic")

        topic = job.topic.strip()

        return FacelessBrief(
            job_id=job.job_id,
            topic=topic,
            angle=f"Warum {topic} gerade Aufmerksamkeit bekommt",
            format_type="trend_short",
            target_runtime=60.0,
            hook_direction=f"Das Internet redet gerade über {topic}",
            scene_plan=[
                f"Hook zu {topic}",
                f"Erklärung des Trends {topic}",
                f"Warum {topic} viral geht",
                f"Kurzer Abschluss mit CTA",
            ],
            voiceover_style="energetic_shortform",
            visual_style="fast_trend_visuals",
            brief_confidence=0.75,
        )