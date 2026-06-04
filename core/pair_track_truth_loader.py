from __future__ import annotations
from pathlib import Path
import json
_DEFAULT_PATH = Path("video_configs/pair_track_truth.json")
def load_truth(path: Path = _DEFAULT_PATH) -> dict:
    """Load the full pair track truth JSON. Returns dict keyed by pair_id."""
    return json.loads(path.read_text(encoding="utf-8-sig"))["pairs"]
def get_ali_source(pair_id: str, path: Path = _DEFAULT_PATH) -> str:
    """Return ali_source track string for a given pair_id (e.g. 'a0', 'a1')."""
    truth = load_truth(path)
    return truth[pair_id]["ali_source"]
def get_friend_tracks(pair_id: str, path: Path = _DEFAULT_PATH) -> list[str]:
    """Return list of friend track strings for a given pair_id. Empty list if none."""
    truth = load_truth(path)
    return truth[pair_id].get("friend_tracks", [])
def get_game_tracks(pair_id: str, path: Path = _DEFAULT_PATH) -> list[str]:
    """Return list of game track strings for a given pair_id. Empty list if none."""
    truth = load_truth(path)
    return truth[pair_id].get("game_tracks", [])
def is_duo(pair_id: str, path: Path = _DEFAULT_PATH) -> bool:
    """Return True if pair is a duo (has friend track)."""
    truth = load_truth(path)
    return truth[pair_id].get("pair_type") == "duo"