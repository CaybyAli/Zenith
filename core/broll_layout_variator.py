from __future__ import annotations

from typing import Any


MAX_CONSECUTIVE_SAME_LAYOUT = 2


class BrollLayoutVariator:
    @staticmethod
    def apply_variation(
        instructions: list[dict],
        max_consecutive: int = MAX_CONSECUTIVE_SAME_LAYOUT,
    ) -> list[dict]:
        """
        Prüft aufeinanderfolgende Einträge auf gleichen layout_type.
        Wenn > max_consecutive gleiche in Folge: Hint setzen.

        Hint: instruction["layout_variation_hint"] = "vary" (String)
        Nie hart ersetzen — nur Hint hinzufügen.
        Wenn kein layout_type im Eintrag: ignorieren (kein Crash).
        Originalliste nicht mutieren — Kopie zurückgeben.
        """
        if not isinstance(instructions, list):
            return []

        try:
            max_allowed = int(max_consecutive)
        except Exception:
            max_allowed = MAX_CONSECUTIVE_SAME_LAYOUT

        max_allowed = max(1, max_allowed)

        varied: list[dict] = []
        previous_layout: Any = None
        consecutive_count = 0

        for instruction in instructions:
            if not isinstance(instruction, dict):
                varied.append(instruction)
                previous_layout = None
                consecutive_count = 0
                continue

            copied = dict(instruction)
            layout_type = copied.get("layout_type")

            if layout_type is None:
                varied.append(copied)
                previous_layout = None
                consecutive_count = 0
                continue

            if layout_type == previous_layout:
                consecutive_count += 1
            else:
                previous_layout = layout_type
                consecutive_count = 1

            if consecutive_count > max_allowed:
                copied["layout_variation_hint"] = "vary"

            varied.append(copied)

        return varied
