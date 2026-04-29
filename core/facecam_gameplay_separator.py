from __future__ import annotations

from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment


class FacecamGameplaySeparator:
    def _clamp_confidence(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def classify_segment(
        self,
        segment: TimelineSegment,
        candidate: HighlightCandidate | None,
    ) -> dict[str, object]:
        role = segment.segment_role
        candidate_kind = candidate.candidate_kind if candidate else "unknown"
        signal_tags = set(candidate.signal_tags) if candidate else set()

        focus_kind = "unknown"
        confidence = 0.5
        notes: list[str] = []

        if role == "hook":
            if candidate_kind == "speech_peak":
                focus_kind = "facecam"
                confidence = 0.88
                notes.append("hook_speech_peak_facecam_priority")
            elif candidate_kind == "action_peak":
                focus_kind = "balanced"
                confidence = 0.76
                notes.append("hook_action_peak_balanced_priority")
            else:
                focus_kind = "facecam"
                confidence = 0.70
                notes.append("hook_default_facecam_bias")

        elif role == "peak":
            if candidate_kind == "action_peak":
                focus_kind = "gameplay"
                confidence = 0.91
                notes.append("peak_action_peak_gameplay_priority")
            elif candidate_kind == "speech_peak":
                focus_kind = "balanced"
                confidence = 0.74
                notes.append("peak_speech_peak_balanced_priority")
            else:
                focus_kind = "gameplay"
                confidence = 0.72
                notes.append("peak_default_gameplay_bias")

        elif role == "payoff":
            if candidate_kind == "speech_peak":
                focus_kind = "balanced"
                confidence = 0.82
                notes.append("payoff_speech_peak_balanced_priority")
            elif candidate_kind == "action_peak":
                focus_kind = "balanced"
                confidence = 0.75
                notes.append("payoff_action_peak_balanced_priority")
            else:
                focus_kind = "balanced"
                confidence = 0.68
                notes.append("payoff_default_balanced_bias")

        elif role == "build":
            focus_kind = "balanced"
            confidence = 0.72
            notes.append("build_segment_balanced_priority")

        elif role == "bridge":
            # KRITISCHER FIX: BRIDGE-Segmente sind IMMER balanced (Gameplay-fokussiert)
            # Signal-Tag-Overrides werden für Bridges NICHT angewendet
            focus_kind = "balanced"
            confidence = 0.72
            notes.append("bridge_segment_balanced_priority_locked")
            
            # Return sofort, bevor Signal-Tag-Overrides greifen
            return {
                "focus_kind": focus_kind,
                "confidence": self._clamp_confidence(confidence),
                "notes": notes,
            }

        # Signal-Tag-Overrides (gelten NICHT für bridge-Segmente)
        if "intro_zone" in signal_tags and focus_kind == "balanced":
            focus_kind = "facecam"
            confidence = max(confidence, 0.73)
            notes.append("intro_zone_facecam_shift")

        if "outro_zone" in signal_tags and focus_kind == "gameplay":
            focus_kind = "balanced"
            confidence = max(confidence, 0.70)
            notes.append("outro_zone_balanced_shift")

        return {
            "focus_kind": focus_kind,
            "confidence": self._clamp_confidence(confidence),
            "notes": notes,
        }