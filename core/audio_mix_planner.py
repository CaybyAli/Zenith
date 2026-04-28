from __future__ import annotations

import uuid

from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline


class AudioMixPlanner:
    def _make_instruction_id(self) -> str:
        return f"mix_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def build_mix_instructions(
        self,
        *,
        timeline: EditTimeline,
        dynamic_edit_plan: DynamicEditPlan,
        audio_cues: list[AudioCue],
    ) -> list[AudioMixInstruction]:
        cue_by_segment = {cue.segment_id: cue for cue in audio_cues}
        pacing_by_segment: dict[str, dict] = {
            hint["segment_id"]: hint
            for hint in dynamic_edit_plan.pacing_hints
            if isinstance(hint, dict) and hint.get("segment_id")
        }

        instructions: list[AudioMixInstruction] = []

        for segment in timeline.selected_segments:
            cue = cue_by_segment.get(segment.segment_id)
            pacing_hint = pacing_by_segment.get(segment.segment_id, {})

            cue_kind = cue.cue_kind if cue else "transition_bed"
            pacing_strength = float(pacing_hint.get("strength", 0.0))

            if segment.segment_role == "hook":
                voice_priority = 0.92
                music_level = 0.42
                ducking_required = True
            elif segment.segment_role == "peak":
                voice_priority = 0.74
                music_level = 0.72
                ducking_required = True
            elif segment.segment_role == "build":
                voice_priority = 0.82
                music_level = 0.56
                ducking_required = True
            elif segment.segment_role == "bridge":
                voice_priority = 0.88
                music_level = 0.36
                ducking_required = True
            elif segment.segment_role == "payoff":
                voice_priority = 0.80
                music_level = 0.48
                ducking_required = True
            else:
                voice_priority = 0.84
                music_level = 0.44
                ducking_required = True

            if cue_kind == "peak_hit":
                music_level = max(music_level, 0.76)
                voice_priority = min(voice_priority, 0.78)

            if cue_kind == "calm_bed":
                music_level = min(music_level, 0.30)
                voice_priority = max(voice_priority, 0.88)

            music_level = self._clamp((music_level * 0.8) + (pacing_strength * 0.2))
            voice_priority = self._clamp(voice_priority)

            instructions.append(
                AudioMixInstruction(
                    instruction_id=self._make_instruction_id(),
                    segment_id=segment.segment_id,
                    voice_priority=voice_priority,
                    music_level=music_level,
                    ducking_required=ducking_required,
                    notes=[
                        f"segment_role={segment.segment_role}",
                        f"cue_kind={cue_kind}",
                        f"pacing_strength={round(pacing_strength, 3)}",
                    ],
                )
            )

        return instructions