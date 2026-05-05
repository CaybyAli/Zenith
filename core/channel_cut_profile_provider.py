from __future__ import annotations

from models.cut_scoring_profile import CutScoringProfile, CutScoringProfileResult


class ChannelCutProfileProvider:
    engine = "channel-cut-profile-v1"

    _CHANNEL_ALIAS: dict[str, str] = {
        "faceless_trend": "faceless",
    }

    def _normalise(self, raw: str | None) -> str:
        if not raw:
            return "default"
        normalised = str(getattr(raw, "value", raw)).strip().lower()
        return self._CHANNEL_ALIAS.get(normalised, normalised)

    def _make_gaming_main(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="gaming_main",
            channel_type="gaming_main",
            description="Fast-cut highlight reel; rewards action flashes and penalises dead air hard.",
            indicator_weights={
                "goal_or_save_like_flash": 1.3,
                "high_action_burst": 1.2,
                "facecam_reaction_spike": 0.9,
                "shock_like": 0.8,
                "sustained_action": 0.8,
                "energy_peak": 0.7,
                "hook_sentence": 1.0,
                "gameplay_action": 0.6,
                "laugh_like_face": 0.5,
                "mouth_open_like": 0.4,
                "silence_or_dead_air": -1.3,
                "round_end_dead_time": -1.2,
                "menu_or_idle": -1.0,
                "low_gameplay_value": -0.8,
                "speech_cut_risk_audio": -0.5,
                "low_facecam_value": -0.4,
                "filler_sentence": -0.6,
            },
            positive_indicator_types=[
                "goal_or_save_like_flash", "high_action_burst", "facecam_reaction_spike",
                "shock_like", "sustained_action", "energy_peak", "hook_sentence",
            ],
            negative_indicator_types=[
                "silence_or_dead_air", "round_end_dead_time", "menu_or_idle",
                "low_gameplay_value", "filler_sentence",
            ],
            neutral_indicator_types=["speech_segment", "speech_active", "scene_change"],
            min_segment_duration_seconds=2.5,
            max_segment_duration_seconds=18.0,
            target_pacing="aggressive",
            speech_safety_weight=0.8,
            gameplay_weight=1.5,
            facecam_weight=1.2,
            audio_reaction_weight=1.1,
            story_weight=0.6,
            dead_air_penalty_weight=1.5,
            micro_cut_penalty_weight=0.8,
            duplicate_penalty_weight=1.0,
        )

    def _make_gaming_uncut(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="gaming_uncut",
            channel_type="gaming_uncut",
            description="Longer uncut gaming footage; favours sustained action over flash moments.",
            indicator_weights={
                "sustained_action": 1.0,
                "goal_or_save_like_flash": 1.0,
                "high_action_burst": 0.9,
                "energy_peak": 0.6,
                "gameplay_action": 0.5,
                "hook_sentence": 0.6,
                "silence_or_dead_air": -0.8,
                "round_end_dead_time": -0.9,
                "menu_or_idle": -0.7,
                "low_gameplay_value": -0.6,
                "filler_sentence": -0.4,
            },
            positive_indicator_types=["sustained_action", "goal_or_save_like_flash", "high_action_burst"],
            negative_indicator_types=["silence_or_dead_air", "round_end_dead_time", "menu_or_idle"],
            neutral_indicator_types=["speech_segment", "speech_active"],
            min_segment_duration_seconds=5.0,
            max_segment_duration_seconds=30.0,
            target_pacing="moderate",
            speech_safety_weight=0.9,
            gameplay_weight=1.3,
            facecam_weight=0.8,
            audio_reaction_weight=0.8,
            story_weight=0.5,
            dead_air_penalty_weight=1.1,
            micro_cut_penalty_weight=0.6,
            duplicate_penalty_weight=1.0,
        )

    def _make_vlog_main(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="vlog_main",
            channel_type="vlog_main",
            description="Story-driven vlog; speech and narrative arcs matter most.",
            indicator_weights={
                "hook_sentence": 1.2,
                "speech_sentence": 0.8,
                "question_sentence": 0.7,
                "exclamation_sentence": 0.6,
                "speech_active": 0.5,
                "facecam_reaction_spike": 0.5,
                "energy_peak": 0.3,
                "gameplay_action": 0.2,
                "silence_or_dead_air": -1.0,
                "filler_sentence": -0.8,
                "incomplete_sentence": -0.5,
                "speech_cut_risk_audio": -0.7,
                "round_end_dead_time": -0.4,
            },
            positive_indicator_types=["hook_sentence", "speech_sentence", "question_sentence"],
            negative_indicator_types=["silence_or_dead_air", "filler_sentence", "incomplete_sentence"],
            neutral_indicator_types=["speech_segment", "energy_activity"],
            min_segment_duration_seconds=4.0,
            max_segment_duration_seconds=45.0,
            target_pacing="slow",
            speech_safety_weight=1.5,
            gameplay_weight=0.4,
            facecam_weight=1.0,
            audio_reaction_weight=1.0,
            story_weight=1.5,
            dead_air_penalty_weight=1.2,
            micro_cut_penalty_weight=1.0,
            duplicate_penalty_weight=1.0,
        )

    def _make_vlog_uncut(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="vlog_uncut",
            channel_type="vlog_uncut",
            description="Relaxed long-form vlog; minimal cuts, speech safety is paramount.",
            indicator_weights={
                "hook_sentence": 1.0,
                "speech_sentence": 0.7,
                "speech_active": 0.5,
                "silence_or_dead_air": -0.8,
                "filler_sentence": -0.6,
                "incomplete_sentence": -0.4,
                "speech_cut_risk_audio": -0.9,
            },
            positive_indicator_types=["hook_sentence", "speech_sentence"],
            negative_indicator_types=["silence_or_dead_air", "filler_sentence", "speech_cut_risk_audio"],
            neutral_indicator_types=["speech_segment", "speech_active"],
            min_segment_duration_seconds=8.0,
            max_segment_duration_seconds=60.0,
            target_pacing="relaxed",
            speech_safety_weight=1.8,
            gameplay_weight=0.2,
            facecam_weight=0.8,
            audio_reaction_weight=0.9,
            story_weight=1.6,
            dead_air_penalty_weight=0.9,
            micro_cut_penalty_weight=1.2,
            duplicate_penalty_weight=0.8,
        )

    def _make_reaction_uncut(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="reaction_uncut",
            channel_type="reaction_uncut",
            description="Reaction content; group reactions and shock moments drive value.",
            indicator_weights={
                "facecam_reaction_spike": 1.1,
                "group_reaction_like": 1.2,
                "shock_like": 1.0,
                "laugh_like_face": 0.9,
                "mouth_open_like": 0.6,
                "expression_change_like": 0.5,
                "shout_like_audio": 0.7,
                "hook_sentence": 0.7,
                "silence_or_dead_air": -0.9,
                "low_facecam_value": -0.8,
                "filler_sentence": -0.5,
                "speech_cut_risk_audio": -0.6,
            },
            positive_indicator_types=[
                "group_reaction_like", "shock_like", "facecam_reaction_spike",
                "laugh_like_face", "shout_like_audio",
            ],
            negative_indicator_types=["silence_or_dead_air", "low_facecam_value"],
            neutral_indicator_types=["speech_segment", "speech_active"],
            min_segment_duration_seconds=4.0,
            max_segment_duration_seconds=40.0,
            target_pacing="moderate",
            speech_safety_weight=1.0,
            gameplay_weight=0.3,
            facecam_weight=1.6,
            audio_reaction_weight=1.4,
            story_weight=0.5,
            dead_air_penalty_weight=1.1,
            micro_cut_penalty_weight=0.9,
            duplicate_penalty_weight=1.0,
        )

    def _make_faceless(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="faceless",
            channel_type="faceless",
            description="No facecam; trend and gameplay value drives selection.",
            indicator_weights={
                "hook_sentence": 1.1,
                "goal_or_save_like_flash": 0.9,
                "high_action_burst": 0.8,
                "energy_peak": 0.7,
                "gameplay_action": 0.6,
                "sustained_action": 0.6,
                "silence_or_dead_air": -1.0,
                "menu_or_idle": -0.8,
                "low_gameplay_value": -0.7,
                "round_end_dead_time": -0.8,
                "filler_sentence": -0.5,
            },
            positive_indicator_types=["hook_sentence", "goal_or_save_like_flash", "high_action_burst"],
            negative_indicator_types=["silence_or_dead_air", "menu_or_idle", "low_gameplay_value"],
            neutral_indicator_types=["speech_segment", "energy_activity"],
            min_segment_duration_seconds=3.0,
            max_segment_duration_seconds=25.0,
            target_pacing="moderate",
            speech_safety_weight=0.6,
            gameplay_weight=1.4,
            facecam_weight=0.0,
            audio_reaction_weight=0.8,
            story_weight=0.7,
            dead_air_penalty_weight=1.3,
            micro_cut_penalty_weight=0.8,
            duplicate_penalty_weight=1.0,
        )

    def _make_shorts(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="shorts",
            channel_type="shorts",
            description="Sub-60s shorts; hook-first, zero dead air tolerance.",
            indicator_weights={
                "hook_sentence": 1.5,
                "goal_or_save_like_flash": 1.4,
                "high_action_burst": 1.2,
                "facecam_reaction_spike": 1.0,
                "shock_like": 0.9,
                "sustained_action": 0.7,
                "silence_or_dead_air": -2.0,
                "menu_or_idle": -1.8,
                "round_end_dead_time": -1.5,
                "low_gameplay_value": -1.3,
                "filler_sentence": -1.0,
                "incomplete_sentence": -0.8,
                "speech_cut_risk_audio": -0.7,
            },
            positive_indicator_types=["hook_sentence", "goal_or_save_like_flash", "high_action_burst"],
            negative_indicator_types=[
                "silence_or_dead_air", "menu_or_idle", "round_end_dead_time", "filler_sentence",
            ],
            neutral_indicator_types=["speech_segment"],
            min_segment_duration_seconds=1.5,
            max_segment_duration_seconds=8.0,
            target_pacing="aggressive",
            speech_safety_weight=0.7,
            gameplay_weight=1.3,
            facecam_weight=1.1,
            audio_reaction_weight=1.0,
            story_weight=0.8,
            dead_air_penalty_weight=2.0,
            micro_cut_penalty_weight=0.5,
            duplicate_penalty_weight=1.2,
        )

    def _make_default(self) -> CutScoringProfile:
        return CutScoringProfile(
            profile_name="default",
            channel_type="default",
            description="Balanced fallback profile for unrecognised channel types.",
            indicator_weights={
                "hook_sentence": 0.8,
                "high_action_burst": 0.7,
                "goal_or_save_like_flash": 0.7,
                "energy_peak": 0.5,
                "facecam_reaction_spike": 0.5,
                "silence_or_dead_air": -0.8,
                "round_end_dead_time": -0.7,
                "menu_or_idle": -0.6,
                "filler_sentence": -0.5,
            },
            positive_indicator_types=["hook_sentence", "high_action_burst", "energy_peak"],
            negative_indicator_types=["silence_or_dead_air", "round_end_dead_time", "menu_or_idle"],
            neutral_indicator_types=["speech_segment", "speech_active"],
            min_segment_duration_seconds=3.0,
            max_segment_duration_seconds=30.0,
            target_pacing="balanced",
            speech_safety_weight=1.0,
            gameplay_weight=1.0,
            facecam_weight=1.0,
            audio_reaction_weight=1.0,
            story_weight=1.0,
            dead_air_penalty_weight=1.0,
            micro_cut_penalty_weight=1.0,
            duplicate_penalty_weight=1.0,
        )

    _PROFILE_BUILDERS = {
        "gaming_main":    "_make_gaming_main",
        "gaming_uncut":   "_make_gaming_uncut",
        "vlog_main":      "_make_vlog_main",
        "vlog_uncut":     "_make_vlog_uncut",
        "reaction_uncut": "_make_reaction_uncut",
        "faceless":       "_make_faceless",
        "shorts":         "_make_shorts",
    }

    def get_profile(
        self,
        channel_type: str | None,
        target_format: str | None = None,
    ) -> CutScoringProfile:
        key = self._normalise(channel_type)

        if target_format is not None:
            fmt = str(getattr(target_format, "value", target_format)).strip().lower()
            if fmt == "short" and key not in ("shorts",):
                key = "shorts"

        builder_name = self._PROFILE_BUILDERS.get(key)
        if builder_name:
            return getattr(self, builder_name)()
        return self._make_default()

    def get_profile_result(
        self,
        channel_type: str | None,
        target_format: str | None = None,
    ) -> CutScoringProfileResult:
        profile = self.get_profile(channel_type, target_format)
        return CutScoringProfileResult(profile=profile, engine=self.engine)
