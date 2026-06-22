from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import blockd_a2b3a_shadow_report as shadow_script


class _Inventory:
    def __init__(self, stream_indexes: list[int]) -> None:
        self.streams = [SimpleNamespace(index=index) for index in stream_indexes]

    def to_dict(self) -> dict[str, list[dict[str, int]]]:
        return {"streams": [{"index": stream.index} for stream in self.streams]}


class _Inspector:
    def __init__(self, inventory: _Inventory) -> None:
        self.inventory = inventory
        self.inspected_path: str | None = None

    def inspect(self, path: str) -> _Inventory:
        self.inspected_path = path
        return self.inventory


def test_pair009_default_paths_remain_pair009() -> None:
    assert shadow_script.DEFAULT_PAIR_ID == "pair_009"
    assert shadow_script._default_raw_path("pair_009") == (
        shadow_script.ROOT / "learning_corpus" / "pairs" / "pair_009" / "raw.mp4"
    )
    assert shadow_script._default_output_path("pair_009") == (
        shadow_script.OUTPUT_DIR / "pair_009_shadow_report.json"
    )
    assert shadow_script._default_job_path("pair_009") == shadow_script.DEFAULT_JOB_PATH


def test_pair006_defaults_do_not_reuse_pair009_job() -> None:
    assert shadow_script._default_raw_path("pair_006") == (
        shadow_script.ROOT / "learning_corpus" / "pairs" / "pair_006" / "raw.mp4"
    )
    assert shadow_script._default_output_path("pair_006") == (
        shadow_script.OUTPUT_DIR / "pair_006_shadow_report.json"
    )
    assert shadow_script._default_job_path("pair_006") is None


def test_absolute_friend_stream_index_uses_ffmpeg_stream_index() -> None:
    inspector = _Inspector(_Inventory([1, 2, 3]))
    processor = SimpleNamespace(audio_stream_inspector=inspector)

    stream_index, inventory = shadow_script._resolve_absolute_audio_stream_index(
        processor,
        Path("raw.mp4"),
        2,
    )

    assert stream_index == 2
    assert inventory == {"streams": [{"index": 1}, {"index": 2}, {"index": 3}]}
    assert inspector.inspected_path == "raw.mp4"


def test_absolute_friend_stream_index_rejects_missing_stream() -> None:
    processor = SimpleNamespace(audio_stream_inspector=_Inspector(_Inventory([1, 3])))

    with pytest.raises(RuntimeError, match="Friend audio stream index 2 not found"):
        shadow_script._resolve_absolute_audio_stream_index(
            processor,
            Path("raw.mp4"),
            2,
        )
