from __future__ import annotations

from core.shorts_transcript_caption_builder import build_caption_words_from_transcript
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


def _result(segments: list[TranscriptSegment]) -> TranscriptResult:
    return TranscriptResult(
        source_path="unit.mp4",
        language="de",
        segments=segments,
        full_text=" ".join(segment.text for segment in segments),
        engine="unit",
    )


def _word(start: float, text: str, probability: float | None = None) -> TranscriptWord:
    return TranscriptWord(
        start_seconds=start,
        end_seconds=start + 0.2,
        text=text,
        probability=probability,
    )


def test_builds_words_from_word_timestamps() -> None:
    transcript = _result(
        [
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=4.0,
                text="a b c d",
                words=[
                    _word(0.0, "A", 0.1),
                    _word(1.0, "B", 0.2),
                    _word(2.0, "C", 0.3),
                    _word(3.0, "D", 0.4),
                ],
            ),
            TranscriptSegment(
                start_seconds=4.0,
                end_seconds=8.0,
                text="e f g h",
                words=[
                    _word(4.0, "E", 0.5),
                    _word(5.0, "F", 0.6),
                    _word(6.0, "G", 0.7),
                    _word(7.0, "H", 0.8),
                ],
            ),
            TranscriptSegment(
                start_seconds=8.0,
                end_seconds=12.0,
                text="i j k l",
                words=[
                    _word(8.0, "I", 0.9),
                    _word(9.0, "J", 1.0),
                    _word(10.0, "K", 0.4),
                    _word(11.0, "L", 0.3),
                ],
            ),
        ]
    )

    words, scores = build_caption_words_from_transcript(
        transcript,
        clip_start_seconds=3.0,
        clip_end_seconds=7.0,
        max_words=9,
    )

    assert words == ["D", "E", "F", "G", "H"]
    assert scores == {
        "d": 0.4,
        "e": 0.5,
        "f": 0.6,
        "g": 0.7,
        "h": 0.8,
    }


def test_falls_back_to_segment_text_if_no_words() -> None:
    transcript = _result(
        [
            TranscriptSegment(
                start_seconds=10.0,
                end_seconds=12.0,
                text="echte worte hier",
            )
        ]
    )

    words, scores = build_caption_words_from_transcript(
        transcript,
        clip_start_seconds=9.5,
        clip_end_seconds=12.5,
        max_words=9,
    )

    assert words == ["echte", "worte", "hier"]
    assert scores == {
        "echte": 0.5,
        "worte": 0.5,
        "hier": 0.5,
    }


def test_empty_result_outside_clip_range() -> None:
    transcript = _result(
        [
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=2.0,
                text="outside range",
                words=[_word(0.5, "outside", 0.9)],
            )
        ]
    )

    words, scores = build_caption_words_from_transcript(
        transcript,
        clip_start_seconds=10.0,
        clip_end_seconds=12.0,
        max_words=9,
    )

    assert words == []
    assert scores == {}


def test_caps_at_max_words() -> None:
    transcript = _result(
        [
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=20.0,
                text="many words",
                words=[_word(float(i), f"w{i}", 0.5) for i in range(20)],
            )
        ]
    )

    words, scores = build_caption_words_from_transcript(
        transcript,
        clip_start_seconds=0.0,
        clip_end_seconds=20.0,
        max_words=9,
    )

    assert words == [f"w{i}" for i in range(9)]
    assert len(scores) == 9
