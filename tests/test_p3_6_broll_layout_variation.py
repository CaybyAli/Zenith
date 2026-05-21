from core.broll_layout_variator import (
    BrollLayoutVariator,
    MAX_CONSECUTIVE_SAME_LAYOUT,
)


def test_two_same_layouts_get_hint():
    """3 gleiche layout_type in Folge → dritter bekommt layout_variation_hint='vary'."""
    instructions = [
        {"layout_type": "closeup"},
        {"layout_type": "closeup"},
        {"layout_type": "closeup"},
    ]

    result = BrollLayoutVariator.apply_variation(
        instructions,
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert "layout_variation_hint" not in result[0]
    assert "layout_variation_hint" not in result[1]
    assert result[2]["layout_variation_hint"] == "vary"


def test_one_same_layout_no_hint():
    """Nur 1 Segment → kein Hint gesetzt."""
    result = BrollLayoutVariator.apply_variation(
        [{"layout_type": "wide"}],
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert result == [{"layout_type": "wide"}]


def test_no_available_alternative_keeps_layout():
    """Wenn alle gleich und max=2: Hints gesetzt, aber layout_type unverändert."""
    instructions = [
        {"layout_type": "wide"},
        {"layout_type": "wide"},
        {"layout_type": "wide"},
        {"layout_type": "wide"},
    ]

    result = BrollLayoutVariator.apply_variation(
        instructions,
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert [item["layout_type"] for item in result] == [
        "wide",
        "wide",
        "wide",
        "wide",
    ]
    assert result[2]["layout_variation_hint"] == "vary"
    assert result[3]["layout_variation_hint"] == "vary"


def test_mixed_layouts_no_hint():
    """Abwechselnde Layouts → kein Hint."""
    instructions = [
        {"layout_type": "wide"},
        {"layout_type": "closeup"},
        {"layout_type": "wide"},
        {"layout_type": "closeup"},
    ]

    result = BrollLayoutVariator.apply_variation(
        instructions,
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert all("layout_variation_hint" not in item for item in result)


def test_no_layout_type_field_does_not_crash():
    """Eintrag ohne layout_type-Feld → kein Crash, keine Änderung."""
    instructions = [
        {"layout_type": "wide"},
        {"note": "no layout"},
        {"layout_type": "wide"},
    ]

    result = BrollLayoutVariator.apply_variation(
        instructions,
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert result == instructions


def test_original_list_not_mutated():
    """apply_variation gibt neue Liste zurück, Original unverändert."""
    instructions = [
        {"layout_type": "wide"},
        {"layout_type": "wide"},
        {"layout_type": "wide"},
    ]

    result = BrollLayoutVariator.apply_variation(
        instructions,
        max_consecutive=MAX_CONSECUTIVE_SAME_LAYOUT,
    )

    assert result is not instructions
    assert result[0] is not instructions[0]
    assert instructions == [
        {"layout_type": "wide"},
        {"layout_type": "wide"},
        {"layout_type": "wide"},
    ]
    assert result[2]["layout_variation_hint"] == "vary"
