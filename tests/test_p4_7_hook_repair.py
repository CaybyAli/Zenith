from __future__ import annotations

from scripts.p4_7_5_rerun_hook import classify_hook_pattern, first_words_from_transcript


def test_hook_pattern_classifier_detects_questions_and_reactions() -> None:
    assert classify_hook_pattern("Was passiert hier jetzt", "de") == "question"
    assert classify_hook_pattern("Oh mein Gott das war knapp", "de") == "high_reaction"
    assert classify_hook_pattern("SOFORT LOS JETZT!", "de") == "exclamation"
    assert classify_hook_pattern("So meine Freunde willkommen zurück", "de") == "narrative"


def test_first_words_from_transcript_limits_word_count() -> None:
    text = " ".join(f"wort{i}" for i in range(30))

    first_words = first_words_from_transcript({"first_10s_text": text}, max_words=18)

    assert len(first_words.split()) == 18
