"""
core/faceless_pipeline.py

Full runner for faceless_trend jobs.

Flow
----
  Job (topic)
    → FacelessBriefBuilder   – rule-based content brief
    → FacelessAssetBuilder   – script + visual/music plan
    → _GPT4oEnricher         – title / description / tags via OpenAI GPT-4o
                               (falls back to rule-based if key is absent)
    → FacelessAssembler      – video assembly (copies stub / real video)
    → ThumbnailForge         – extract thumbnail frames
    → Validator              – blocking-issue check
    → _write_outputs()       – metadata.json  +  canonical thumbnail.jpg
    → return result dict     – status "waiting_for_review"
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from core.faceless_assembler import FacelessAssembler
from core.faceless_asset_builder import FacelessAssetBuilder
from core.faceless_brief_builder import FacelessBriefBuilder
from core.thumbnail_forge import ThumbnailForge
from core.validator import Validator
from models.faceless_asset_pack import FacelessAssetPack
from models.faceless_brief import FacelessBrief
from models.job import Job
from models.metadata_package import MetadataPackage
from models.thumbnail_package import ThumbnailPackage
from models.title_package import TitlePackage
from shared.errors import ValidationError


# ------------------------------------------------------------------ #
#  GPT-4o enricher                                                     #
# ------------------------------------------------------------------ #

class _GPT4oEnricher:
    """
    Calls OpenAI GPT-4o to generate a YouTube-optimised title,
    description and tags for a faceless trend video.

    Returns None (silently) when:
      - OPENAI_API_KEY is not set
      - the openai package is not installed
      - any API / network error occurs
    """

    MODEL = "gpt-4o"

    def _build_prompt(self, topic: str, hook: str, script_excerpt: str) -> str:
        return (
            "Du bist ein YouTube-Content-Stratege für virale Trend-Videos.\n\n"
            f"Thema: {topic}\n"
            f"Hook-Richtung: {hook}\n"
            f"Script-Auszug: {script_excerpt[:300]}\n\n"
            "Generiere:\n"
            "1. Titel (max 100 Zeichen, klickstark, auf Deutsch, ohne Emojis am Anfang)\n"
            "2. Beschreibung (300-400 Zeichen, Kontext + CTA)\n"
            "3. Tags (genau 8 relevante Tags, kommagetrennt)\n\n"
            "Antworte exakt in diesem Format – keine zusätzlichen Zeilen:\n"
            "TITEL: ...\n"
            "BESCHREIBUNG: ...\n"
            "TAGS: ...\n"
        )

    def _parse_response(self, text: str) -> dict[str, object]:
        result: dict[str, object] = {}
        for line in text.strip().splitlines():
            if line.startswith("TITEL:"):
                result["title"] = line[len("TITEL:"):].strip()
            elif line.startswith("BESCHREIBUNG:"):
                result["description"] = line[len("BESCHREIBUNG:"):].strip()
            elif line.startswith("TAGS:"):
                raw_tags = line[len("TAGS:"):].strip()
                result["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]
        return result

    def enrich(
        self,
        *,
        topic: str,
        hook: str,
        script_excerpt: str,
    ) -> dict[str, object] | None:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            import openai  # type: ignore[import]
        except ImportError:
            return None

        try:
            client = openai.OpenAI(api_key=api_key)
            prompt = self._build_prompt(topic, hook, script_excerpt)
            response = client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.7,
            )
            raw = response.choices[0].message.content or ""
            parsed = self._parse_response(raw)
            if "title" not in parsed:
                return None
            return parsed
        except Exception:
            return None


# ------------------------------------------------------------------ #
#  Title / Metadata builders                                           #
# ------------------------------------------------------------------ #

def _build_title_package(
    job: Job,
    gpt_data: dict[str, object] | None,
) -> TitlePackage:
    if gpt_data and gpt_data.get("title"):
        primary = str(gpt_data["title"])
        backups = [
            f"Warum {job.topic} gerade viral geht",
            f"{job.topic} – das steckt dahinter",
        ]
        score = 0.88
    else:
        primary = f"{job.topic} – das geht viral 😳"
        backups = [
            f"Warum {job.topic} gerade im Trend ist",
            f"Das Internet dreht durch wegen {job.topic}",
        ]
        score = 0.70

    return TitlePackage(
        job_id=job.job_id,
        primary_title=primary,
        backup_titles=backups,
        title_score=score,
    )


def _build_metadata_package(
    job: Job,
    title_package: TitlePackage,
    gpt_data: dict[str, object] | None,
) -> MetadataPackage:
    if gpt_data and gpt_data.get("description"):
        description = str(gpt_data["description"])
    else:
        description = (
            f"{title_package.primary_title}\n\n"
            f"In diesem Video schauen wir uns an, warum {job.topic} gerade "
            f"viral geht und so viele Menschen beschäftigt.\n\n"
            "Folge dem Kanal für tägliche Trend-Analysen!"
        )

    if gpt_data and gpt_data.get("tags"):
        hashtags = [
            f"#{t.lstrip('#')}" for t in list(gpt_data["tags"])[:8]
        ]
    else:
        topic_tag = job.topic.replace(" ", "").lower()
        hashtags = [
            f"#{topic_tag}",
            "#trend",
            "#viral",
            "#youtube",
            "#shorts",
            "#trending",
        ]

    return MetadataPackage(
        job_id=job.job_id,
        description=description,
        hashtags=hashtags,
    )


# ------------------------------------------------------------------ #
#  Output helpers                                                      #
# ------------------------------------------------------------------ #

def _canonical_thumbnail(
    thumbnail_package: ThumbnailPackage,
    output_dir: Path,
    job_id: str,
) -> str:
    """Copy the selected thumbnail to a stable path → {job_id}_thumbnail.jpg."""
    src = Path(thumbnail_package.selected_thumbnail)
    dst = output_dir / f"{job_id}_thumbnail.jpg"
    if src.exists() and src != dst:
        shutil.copy2(src, dst)
    return str(dst)


def _write_metadata_json(
    *,
    job: Job,
    video_path: str,
    thumbnail_path: str,
    title_package: TitlePackage,
    metadata_package: MetadataPackage,
    validator_result,
    brief: FacelessBrief,
    asset_pack: FacelessAssetPack,
    gpt_used: bool,
    output_dir: Path,
) -> str:
    payload = {
        "job_id": job.job_id,
        "topic": job.topic,
        "status": "waiting_for_review",
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "title": title_package.primary_title,
        "backup_titles": title_package.backup_titles,
        "title_score": title_package.title_score,
        "description": metadata_package.description,
        "hashtags": metadata_package.hashtags,
        "validator_status": validator_result.validator_status,
        "blocking_issues": validator_result.blocking_issues,
        "ready_for_publish": validator_result.ready_for_publish,
        "gpt_metadata_used": gpt_used,
        "brief": {
            "angle": brief.angle,
            "format_type": brief.format_type,
            "target_runtime": brief.target_runtime,
            "hook_direction": brief.hook_direction,
            "scene_plan": brief.scene_plan,
            "voiceover_style": brief.voiceover_style,
            "visual_style": brief.visual_style,
            "brief_confidence": brief.brief_confidence,
        },
        "asset_pack": {
            "voiceover_source": asset_pack.voiceover_source,
            "music_plan": asset_pack.music_plan,
            "asset_pack_confidence": asset_pack.asset_pack_confidence,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = output_dir / f"{job.job_id}_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    return str(out_path)


# ------------------------------------------------------------------ #
#  Public runner                                                       #
# ------------------------------------------------------------------ #

class FacelessPipeline:
    """
    Stateless runner for a single faceless_trend Job.
    Instantiate fresh each call (no shared state).
    """

    def run(self, job: Job) -> dict[str, object]:
        """
        Execute the full faceless pipeline for *job*.

        Returns a result dict with keys:
          job_id, status, video_path, thumbnail_path, metadata_path,
          title, description, hashtags, validator_status,
          ready_for_publish, gpt_metadata_used, brief, asset_pack.

        Raises ValidationError on unrecoverable failures.
        """
        if not job.topic or not job.topic.strip():
            raise ValidationError(f"Job {job.job_id} has no topic set")

        # 1. Brief
        brief: FacelessBrief = FacelessBriefBuilder().build(job)

        # 2. Asset pack
        asset_pack: FacelessAssetPack = FacelessAssetBuilder().build(brief)

        # 3. GPT-4o enrichment (best-effort, non-blocking)
        gpt_data = _GPT4oEnricher().enrich(
            topic=job.topic,
            hook=brief.hook_direction,
            script_excerpt=asset_pack.script_text,
        )
        gpt_used = gpt_data is not None

        # 4. Title + metadata
        title_package = _build_title_package(job, gpt_data)
        metadata_package = _build_metadata_package(job, title_package, gpt_data)

        # 5. Video assembly
        video_path: str = FacelessAssembler().assemble(asset_pack)

        # 6. Thumbnail
        output_dir = Path(video_path).parent
        thumbnail_package: ThumbnailPackage = ThumbnailForge().generate(
            job, video_path
        )
        thumbnail_path = _canonical_thumbnail(
            thumbnail_package, output_dir, job.job_id
        )

        # 7. Validate
        validator_result = Validator().validate(
            job,
            video_path,
            title_package,
            metadata_package,
            thumbnail_package,
        )

        # 8. Write metadata.json
        metadata_path = _write_metadata_json(
            job=job,
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            title_package=title_package,
            metadata_package=metadata_package,
            validator_result=validator_result,
            brief=brief,
            asset_pack=asset_pack,
            gpt_used=gpt_used,
            output_dir=output_dir,
        )

        return {
            "job_id": job.job_id,
            "status": "waiting_for_review",
            "video_path": video_path,
            "thumbnail_path": thumbnail_path,
            "metadata_path": metadata_path,
            "title": title_package.primary_title,
            "description": metadata_package.description,
            "hashtags": metadata_package.hashtags,
            "validator_status": validator_result.validator_status,
            "blocking_issues": validator_result.blocking_issues,
            "ready_for_publish": validator_result.ready_for_publish,
            "gpt_metadata_used": gpt_used,
            "brief": brief,
            "asset_pack": asset_pack,
        }
