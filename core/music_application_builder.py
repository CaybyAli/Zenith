from __future__ import annotations

import uuid

from models.job import Job
from models.local_music_asset import LocalMusicAsset
from models.local_music_selection import LocalMusicSelection
from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan
from models.music_cue_plan import MusicCuePlan


class MusicApplicationBuilder:
    def _make_plan_id(self) -> str:
        return f"music_apply_{uuid.uuid4().hex[:12]}"

    def _make_instruction_id(self) -> str:
        return f"music_apply_instr_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _fade_profile(self, cue_kind: str) -> tuple[float, float]:
        profiles = {
            "intro_bed": (0.35, 0.45),
            "build_up": (0.25, 0.35),
            "peak_hit": (0.10, 0.20),
            "calm_bed": (0.50, 0.60),
            "transition_bed": (0.30, 0.35),
            "tension_bed": (0.22, 0.30),
        }
        return profiles.get(cue_kind, (0.25, 0.25))

    def _cue_key(self, cue_kind: str, start_time: float, end_time: float) -> tuple[str, float, float]:
        return (
            str(cue_kind),
            round(float(start_time), 3),
            round(float(end_time), 3),
        )

    def build(
        self,
        *,
        job: Job,
        music_cue_plan: MusicCuePlan | None,
        local_music_selections: list[LocalMusicSelection],
        assets: list[LocalMusicAsset],
    ) -> MusicApplicationPlan | None:
        if job.channel_type.value != "gaming_main":
            return None

        if music_cue_plan is None:
            return None

        if not local_music_selections:
            return None

        asset_by_id = {
            asset.asset_id: asset
            for asset in assets
            if asset.active
            and asset.channel_type == job.channel_type.value
            and asset.file_path
        }

        cue_by_key = {
            self._cue_key(cue.cue_kind, cue.start_time, cue.end_time): cue
            for cue in music_cue_plan.audio_cues
        }

        mix_by_segment_id = {
            instruction.segment_id: instruction
            for instruction in music_cue_plan.audio_mix_instructions
        }

        application_instructions: list[MusicApplicationInstruction] = []
        score_parts: list[float] = []

        for selection in local_music_selections:
            asset = asset_by_id.get(selection.asset_id)
            if asset is None:
                continue

            cue = cue_by_key.get(
                self._cue_key(
                    selection.cue_kind,
                    selection.start_time,
                    selection.end_time,
                )
            )
            if cue is None:
                continue

            mix_instruction = mix_by_segment_id.get(cue.segment_id)
            if mix_instruction is None:
                continue

            fade_in_seconds, fade_out_seconds = self._fade_profile(selection.cue_kind)

            application_instructions.append(
                MusicApplicationInstruction(
                    instruction_id=self._make_instruction_id(),
                    job_id=job.job_id,
                    channel_type=job.channel_type.value,
                    asset_id=asset.asset_id,
                    cue_kind=selection.cue_kind,
                    source_file_path=asset.file_path,
                    start_time=selection.start_time,
                    end_time=selection.end_time,
                    music_level=mix_instruction.music_level,
                    voice_priority=mix_instruction.voice_priority,
                    ducking_required=mix_instruction.ducking_required,
                    fade_in_seconds=fade_in_seconds,
                    fade_out_seconds=fade_out_seconds,
                    notes=[
                        f"selected_title={asset.title}",
                        f"match_score={selection.match_score}",
                        f"source_provider={asset.source_provider}",
                    ],
                )
            )

            score_parts.append(
                self._clamp(
                    (selection.match_score * 0.6)
                    + (mix_instruction.music_level * 0.25)
                    + ((1.0 - abs(mix_instruction.voice_priority - 0.8)) * 0.15)
                )
            )

        if not application_instructions:
            return None

        application_score = round(sum(score_parts) / len(score_parts), 3) if score_parts else 0.0

        return MusicApplicationPlan(
            plan_id=self._make_plan_id(),
            job_id=job.job_id,
            channel_type=job.channel_type.value,
            instructions=application_instructions,
            application_score=application_score,
            notes=[
                f"instructions={len(application_instructions)}",
                "music_application_enabled_for_channel=true",
                "source=local_epidemic_assets",
            ],
        )