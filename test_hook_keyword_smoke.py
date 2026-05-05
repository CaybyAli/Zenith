from core.hook_keyword_extractor import HookKeywordExtractor
from models.transcript_result import TranscriptResult, TranscriptSegment


def main() -> None:
    extractor = HookKeywordExtractor()

    strong_text = (
        "Das war der krasseste Save meines Lebens. "
        "Ich dachte wirklich, das Spiel ist verloren."
    )

    strong_result = extractor.analyze(text=strong_text)

    assert strong_result.engine == "rule-based-hook-keyword-v1"
    assert strong_result.source_text_length == len(strong_text)
    assert strong_result.keywords, "Expected keywords for strong text"
    assert strong_result.hook_sentences, "Expected hook sentences for strong text"
    assert strong_result.top_hook is not None, "Expected top hook for strong text"

    expected_keywords = {"krasseste", "save", "lebens", "spiel", "verloren"}
    found_keywords = set(strong_result.keywords)

    assert (
        expected_keywords.intersection(found_keywords)
    ), f"Expected at least one strong keyword, got: {strong_result.keywords}"

    top_strong_hook = strong_result.hook_sentences[0]

    assert (
        top_strong_hook.score >= 0.70
    ), f"Expected high hook score, got: {top_strong_hook.score}"

    assert (
        "strong_words" in top_strong_hook.reason
        or "stakes" in top_strong_hook.reason
    ), f"Expected useful hook reason, got: {top_strong_hook.reason}"

    weak_text = "okay ja dann laufen wir hier mal weiter und schauen mal"
    weak_result = extractor.analyze(text=weak_text)

    assert weak_result.engine == "rule-based-hook-keyword-v1"
    assert weak_result.hook_sentences, "Weak text should still return controlled hook scores"

    top_weak_hook = weak_result.hook_sentences[0]

    assert (
        top_weak_hook.score < top_strong_hook.score
    ), f"Weak hook score should be lower than strong hook score: weak={top_weak_hook.score}, strong={top_strong_hook.score}"

    assert (
        top_weak_hook.score <= 0.35
    ), f"Weak filler text should stay low, got: {top_weak_hook.score}"

    assert (
        weak_result.top_hook is None
    ), f"Weak filler text should not dominate as top_hook, got: {weak_result.top_hook}"

    empty_result = extractor.analyze(text="")

    assert empty_result.keywords == []
    assert empty_result.hook_sentences == []
    assert empty_result.top_hook is None
    assert empty_result.source_text_length == 0

    transcript = TranscriptResult(
        source_path="test.mp4",
        language="de",
        engine="test",
        full_text=strong_text,
        segments=[
            TranscriptSegment(
                start_seconds=1.0,
                end_seconds=3.5,
                text="okay ja dann laufen wir hier mal weiter",
                confidence=0.9,
            ),
            TranscriptSegment(
                start_seconds=10.0,
                end_seconds=14.0,
                text="Das war der krasseste Save meines Lebens!",
                confidence=0.95,
            ),
        ],
    )

    segment_result = extractor.analyze(transcript)

    assert segment_result.hook_sentences
    assert segment_result.top_hook == "Das war der krasseste Save meines Lebens!"

    segment_top_hook = segment_result.hook_sentences[0]

    assert segment_top_hook.start_seconds == 10.0
    assert segment_top_hook.end_seconds == 14.0
    assert segment_top_hook.score >= 0.70

    result_dict = segment_result.to_dict()

    assert isinstance(result_dict, dict)
    assert isinstance(result_dict["keywords"], list)
    assert isinstance(result_dict["hook_sentences"], list)
    assert result_dict["top_hook"] == "Das war der krasseste Save meines Lebens!"
    assert result_dict["engine"] == "rule-based-hook-keyword-v1"

    print("HOOK KEYWORD SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
