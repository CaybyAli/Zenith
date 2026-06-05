from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

from core.qwen_side_track import (
    LocalQwenSideTrack,
    QwenSideTrackError,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def fake_ollama_response(model_text: str) -> FakeResponse:
    return FakeResponse({"response": model_text})


def test_rejects_non_local_base_url() -> None:
    with pytest.raises((QwenSideTrackError, ValueError)):
        LocalQwenSideTrack(base_url="https://example.com")


def test_good_ollama_response_returns_analysis_only_result() -> None:
    model_text = (
        '{"status":"ok","role":"analysis_only","can_cut":false,'
        '"confidence":0.5,"notes":["local only"]}'
    )

    with patch(
        "core.qwen_side_track.urllib.request.urlopen",
        return_value=fake_ollama_response(model_text),
    ):
        result = LocalQwenSideTrack().analyze_json_only("safe local probe")

    assert result.status == "ok"
    assert result.role == "analysis_only"
    assert result.can_cut is False
    assert result.confidence == 0.5
    assert result.notes == ["local only"]
    assert result.raw_text == model_text


def test_invalid_model_json_raises() -> None:
    with patch(
        "core.qwen_side_track.urllib.request.urlopen",
        return_value=fake_ollama_response("not json"),
    ):
        with pytest.raises(QwenSideTrackError):
            LocalQwenSideTrack().analyze_json_only("safe local probe")


def test_can_cut_true_raises() -> None:
    model_text = (
        '{"status":"ok","role":"analysis_only","can_cut":true,'
        '"confidence":0.5,"notes":["bad"]}'
    )

    with patch(
        "core.qwen_side_track.urllib.request.urlopen",
        return_value=fake_ollama_response(model_text),
    ):
        with pytest.raises(QwenSideTrackError):
            LocalQwenSideTrack().analyze_json_only("safe local probe")


def test_wrong_role_raises() -> None:
    model_text = (
        '{"status":"ok","role":"primary_cutter","can_cut":false,'
        '"confidence":0.5,"notes":["bad"]}'
    )

    with patch(
        "core.qwen_side_track.urllib.request.urlopen",
        return_value=fake_ollama_response(model_text),
    ):
        with pytest.raises(QwenSideTrackError):
            LocalQwenSideTrack().analyze_json_only("safe local probe")


def test_no_authorization_header_sent() -> None:
    model_text = (
        '{"status":"ok","role":"analysis_only","can_cut":false,'
        '"confidence":0.5,"notes":["local only"]}'
    )

    with patch(
        "core.qwen_side_track.urllib.request.urlopen",
        return_value=fake_ollama_response(model_text),
    ) as mocked_urlopen:
        LocalQwenSideTrack().analyze_json_only("safe local probe")

    request = mocked_urlopen.call_args.args[0]
    headers = {key.lower(): value for key, value in request.header_items()}

    assert "authorization" not in headers
    assert "content-type" in headers or "content-type".lower() in headers


def test_side_track_has_no_cutting_methods() -> None:
    forbidden = {
        "select_clip",
        "choose_cut",
        "build_timeline",
        "rank_candidates",
        "decide",
    }

    method_names = {
        name
        for name, value in inspect.getmembers(LocalQwenSideTrack)
        if callable(value)
    }

    assert forbidden.isdisjoint(method_names)
