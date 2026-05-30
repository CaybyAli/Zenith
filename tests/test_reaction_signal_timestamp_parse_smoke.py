from core.reaction_intensity_signal_builder import parse_reaction_timestamp


def test_reaction_timestamp_decimal_seconds():
    assert parse_reaction_timestamp("00:02:40.500") == 160.5


def test_reaction_timestamp_subsecond_colon_group():
    assert parse_reaction_timestamp("00:01:13:14") == 73.14
