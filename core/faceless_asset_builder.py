from models.faceless_asset_pack import FacelessAssetPack
from models.faceless_brief import FacelessBrief


class FacelessAssetBuilder:
    def build(self, brief: FacelessBrief) -> FacelessAssetPack:
        script_text = (
            f"{brief.hook_direction}. "
            f"Heute schauen wir uns an, warum {brief.topic} gerade viral geht. "
            f"Das Thema taucht immer öfter online auf und zieht viel Aufmerksamkeit. "
            f"Bleib dran, um zu sehen, warum dieser Trend gerade explodiert."
        )

        voiceover_source = "ai_voice_default"

        scene_visual_plan = [
            f"Schneller Hook mit Text zu {brief.topic}",
            f"Trend-Beispiele und visuelle Symbole zu {brief.topic}",
            f"Erklärung, warum {brief.topic} Aufmerksamkeit bekommt",
            f"Abschluss mit starkem CTA Screen",
        ]

        music_plan = "fast_trending_background_music"

        text_overlay_plan = [
            f"{brief.topic} ist gerade überall",
            "Warum geht das viral?",
            "Das steckt dahinter",
            "Folge für mehr Trends",
        ]

        return FacelessAssetPack(
            job_id=brief.job_id,
            script_text=script_text,
            voiceover_source=voiceover_source,
            scene_visual_plan=scene_visual_plan,
            music_plan=music_plan,
            text_overlay_plan=text_overlay_plan,
            asset_pack_confidence=0.78,
        )