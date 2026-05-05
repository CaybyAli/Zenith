from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sentence_timeline_builder import SentenceTimelineBuilder
from models.transcript_result import TranscriptResult, TranscriptSegment


def _transcript(segments: list[TranscriptSegment]) -> TranscriptResult:
    return TranscriptResult(
        source_path="sentence_smoke.mp4",
        language="de",
        segments=segments,
        full_text=" ".join(segment.text for segment in segments),
        engine="smoke-transcript",
    )


def test_empty_inputs_do_not_crash() -> None:
    result = SentenceTimelineBuilder().build(None)

    assert result.sentences == []
    assert result.total_sentences == 0
    assert result.skipped_reason == "no transcript segments"


def test_sentence_timeline_builder_smoke() -> None:
    builder = SentenceTimelineBuilder()
    result = builder.build(
        _transcript(
            [
                TranscriptSegment(0.0, 1.0, "Wir waren komplett tot,", confidence=0.9),
                TranscriptSegment(1.1, 2.4, "aber dann kam Nils mit dem Save!", confidence=0.92),
                TranscriptSegment(4.0, 4.8, "okay ja aehm", confidence=0.8),
                TranscriptSegment(6.0, 7.0, "ich wollte eigentlich aber", confidence=0.7),
                TranscriptSegment(8.5, 9.3, "warum passiert das", confidence=0.85),
                TranscriptSegment(10.6, 11.3, "Alter krass", confidence=0.88),
                TranscriptSegment(12.3, 18.0, "dieser sehr lange satz braucht noch mehr text", confidence=0.8),
                TranscriptSegment(18.1, 24.6, "und wird wegen duration sauber beendet", confidence=0.82),
                TranscriptSegment(25.0, 26.0, "danach kommt der letzte Satz.", confidence=0.9),
            ]
        ),
        max_gap_seconds=0.75,
        max_sentence_duration_seconds=8.0,
    )

    kinds = [sentence.sentence_kind for sentence in result.sentences]
    by_kind = {sentence.sentence_kind: sentence for sentence in result.sentences}
    ended_by_values = {sentence.metadata["ended_by"] for sentence in result.sentences}

    assert result.total_sentences >= 7
    assert result.sentences[0].text == "Wir waren komplett tot, aber dann kam Nils mit dem Save!"
    assert result.sentences[0].sentence_kind == "hook"
    assert result.sentences[0].score >= 0.65
    assert "filler" in kinds
    assert by_kind["filler"].score <= 0.30
    assert "incomplete" in kinds
    assert by_kind["incomplete"].text == "ich wollte eigentlich aber"
    assert "question" in kinds
    assert "exclamation" in kinds
    assert "punctuation" in ended_by_values
    assert "gap" in ended_by_values
    assert "max_duration" in ended_by_values

    payload = result.to_dict()
    assert payload["engine"] == SentenceTimelineBuilder.engine
    assert payload["total_sentences"] == result.total_sentences
    assert payload["hook_sentence_count"] == result.hook_sentence_count
    assert payload["filler_sentence_count"] == result.filler_sentence_count
    assert payload["incomplete_sentence_count"] == result.incomplete_sentence_count

    print("SENTENCE TIMELINE BUILDER SMOKE TEST PASSED")
    print(f"total_sentences={result.total_sentences}")
    print(f"hook_sentence_count={result.hook_sentence_count}")
    print(f"filler_sentence_count={result.filler_sentence_count}")
    print(f"incomplete_sentence_count={result.incomplete_sentence_count}")
    print(f"sentence_kinds={sorted(set(kinds))}")


if __name__ == "__main__":
    test_empty_inputs_do_not_crash()
    test_sentence_timeline_builder_smoke()
