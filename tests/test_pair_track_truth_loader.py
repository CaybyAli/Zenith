from pathlib import Path
from core.pair_track_truth_loader import get_ali_source, get_friend_tracks, is_duo
_TRUTH = Path("video_configs/pair_track_truth.json")
def test_ali_source_pair_001():
    assert get_ali_source("pair_001", _TRUTH) == "a0"
def test_ali_source_pair_008_is_not_a0():
    # pair_008 hat a0=mix, ali ist a1
    assert get_ali_source("pair_008", _TRUTH) == "a1"
def test_friend_tracks_pair_003_empty():
    # pair_003 ist solo -> keine friend tracks
    assert get_friend_tracks("pair_003", _TRUTH) == []
def test_is_duo_pair_001():
    assert is_duo("pair_001", _TRUTH) is True
def test_is_duo_pair_003_false():
    assert is_duo("pair_003", _TRUTH) is False