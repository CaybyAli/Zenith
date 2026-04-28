from __future__ import annotations

import uuid

from models.job import Job
from models.local_music_asset import LocalMusicAsset
from models.local_music_selection import LocalMusicSelection
from models.music_cue_plan import MusicCuePlan


class LocalMusicSelector:
    def _make_selection_id(self) -> str:
        return f"local_music_sel_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _cue_match_score(self, cue_kind: str, asset: LocalMusicAsset) -> float:
        if cue_kind in asset.cue_kinds:
            return 1.0

        soft_map = {
            "intro_bed": {"transition_bed", "calm_bed"},
            "build_up": {"tension_bed", "transition_bed"},
            "peak_hit": {"build_up", "tension_bed"},
            "calm_bed": {"transition_bed", "intro_bed"},
            "transition_bed": {"intro_bed", "calm_bed"},
            "tension_bed": {"build_up", "peak_hit"},
        }

        allowed = soft_map.get(cue_kind, set())
        if any(kind in allowed for kind in asset.cue_kinds):
            return 0.72

        return 0.0

    def _energy_target_for_cue(self, cue_kind: str) -> float:
        mapping = {
            "intro_bed": 0.62,
            "build_up": 0.76,
            "peak_hit": 0.92,
            "calm_bed": 0.30,
            "transition_bed": 0.48,
            "tension_bed": 0.70,
        }
        return mapping.get(cue_kind, 0.55)

    def _energy_match_score(self, cue_kind: str, asset: LocalMusicAsset) -> float:
        target = self._energy_target_for_cue(cue_kind)
        distance = abs(float(asset.energy_level) - target)
        return self._clamp(1.0 - distance)

    def _overall_match_score(self, cue_kind: str, asset: LocalMusicAsset) -> float:
        cue_score = self._cue_match_score(cue_kind, asset)
        if cue_score <= 0:
            return 0.0

        energy_score = self._energy_match_score(cue_kind, asset)
        return self._clamp((cue_score * 0.7) + (energy_score * 0.3))

    def _rank_assets(
        self,
        cue_kind: str,
        assets: list[LocalMusicAsset],
    ) -> list[tuple[LocalMusicAsset, float]]:
        ranked: list[tuple[LocalMusicAsset, float]] = []

        for asset in assets:
            score = self._overall_match_score(cue_kind, asset)
            if score > 0:
                ranked.append((asset, score))

        ranked.sort(
            key=lambda item: (
                -item[1],
                -float(item[0].energy_level),
                item[0].title.lower(),
            )
        )
        return ranked

    def select_for_plan(
        self,
        *,
        job: Job,
        music_cue_plan: MusicCuePlan | None,
        assets: list[LocalMusicAsset],
    ) -> list[LocalMusicSelection]:
        if job.channel_type.value != "gaming_main":
            return []

        if music_cue_plan is None:
            return []

        eligible_assets = [
            asset
            for asset in assets
            if asset.active
            and asset.channel_type == job.channel_type.value
            and asset.file_path
        ]

        if not eligible_assets:
            return []

        selections: list[LocalMusicSelection] = []
        used_asset_ids: set[str] = set()

        for cue in music_cue_plan.audio_cues:
            ranked_assets = self._rank_assets(cue.cue_kind, eligible_assets)

            if not ranked_assets:
                continue

            preferred_unused = [
                (asset, score)
                for asset, score in ranked_assets
                if asset.asset_id not in used_asset_ids
            ]

            chosen_asset: LocalMusicAsset
            chosen_score: float
            reused_fallback = False

            if preferred_unused:
                chosen_asset, chosen_score = preferred_unused[0]
            else:
                chosen_asset, chosen_score = ranked_assets[0]
                reused_fallback = True

            if chosen_score <= 0:
                continue

            used_asset_ids.add(chosen_asset.asset_id)

            notes = [
                f"selected_title={chosen_asset.title}",
                f"source_provider={chosen_asset.source_provider}",
                f"cue_kind={cue.cue_kind}",
            ]

            if reused_fallback:
                notes.append("reused_asset_fallback=true")
            else:
                notes.append("reused_asset_fallback=false")

            selections.append(
                LocalMusicSelection(
                    selection_id=self._make_selection_id(),
                    job_id=job.job_id,
                    channel_type=job.channel_type.value,
                    asset_id=chosen_asset.asset_id,
                    cue_kind=cue.cue_kind,
                    match_score=chosen_score,
                    start_time=cue.start_time,
                    end_time=cue.end_time,
                    notes=notes,
                )
            )

        return selections