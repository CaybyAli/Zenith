from __future__ import annotations

from pathlib import Path

from core.interaction_classifier import classify_interactions, classify_interaction_segment
from models.interaction_classification import (
    InteractionClassificationPoint,
    InteractionClassificationResult,
    InteractionSegmentClassification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def test_interaction_point_roundtrip() -> None:
    point = InteractionClassificationPoint(
        interaction_id="p1",
        text="Nils komm",
        normalized_text="nils komm",
        interaction_type="interaction",
        confidence=0.8,
        context_needed=True,
        is_question=False,
        metadata={"source": "test"},
    )

    restored = InteractionClassificationPoint.from_dict(point.to_dict())

    assert restored.to_dict() == point.to_dict()


def test_segment_classification_roundtrip() -> None:
    segment = InteractionSegmentClassification(
        segment_id="s1",
        text="Chat was meint ihr?",
        interaction_type="chat_reaction",
        confidence=0.75,
        chat_reaction_score=0.8,
        context_needed=True,
    )

    restored = InteractionSegmentClassification.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_interaction_result_roundtrip() -> None:
    result = InteractionClassificationResult(
        status="ok",
        points=[InteractionClassificationPoint(interaction_id="p1")],
        segment_classifications=[
            InteractionSegmentClassification(segment_id="s1")
        ],
        point_count=1,
        segment_classification_count=1,
        monologue_count=1,
    )

    restored = InteractionClassificationResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_monologue_detected() -> None:
    result = classify_interactions(
        [{"start_seconds": 0.0, "end_seconds": 2.0, "text": "Ich bin jetzt hier in der Runde."}]
    )

    assert result.status == "ok"
    assert result.segment_classifications[0].interaction_type == "monologue"


def test_interaction_direct_address_detected() -> None:
    classification = classify_interaction_segment(
        {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Nils komm mal bitte."}
    )

    assert classification.interaction_type == "interaction"
    assert classification.context_needed is True


def test_question_answer_detected() -> None:
    result = classify_interactions(
        [
            {"start_seconds": 0.0, "end_seconds": 1.0, "text": "Wo bist du?"},
            {"start_seconds": 2.0, "end_seconds": 3.0, "text": "Hier vorne."},
        ]
    )

    assert result.segment_classifications[0].interaction_type == "question_answer"
    assert result.segment_classifications[1].interaction_type == "question_answer"


def test_chat_reaction_detected() -> None:
    classification = classify_interaction_segment(
        {"text": "Chat schreibt mal was meint ihr dazu?"}
    )

    assert classification.interaction_type == "chat_reaction"


def test_callout_detected() -> None:
    classification = classify_interaction_segment({"text": "Links oben pass auf!"})

    assert classification.interaction_type == "callout"


def test_private_or_meta_candidate_detected() -> None:
    classification = classify_interaction_segment(
        {"text": "Schneid das raus, technisches Problem."}
    )

    assert classification.interaction_type == "private_or_meta_candidate"
    assert classification.context_needed is True


def test_context_needed_for_question() -> None:
    classification = classify_interaction_segment({"text": "Warum ist das so?"})

    assert classification.context_needed is True


def test_context_needed_for_interaction() -> None:
    classification = classify_interaction_segment({"text": "Bro warte kurz."})

    assert classification.context_needed is True


def test_empty_transcript_skips() -> None:
    result = classify_interactions([])

    assert result.status == "skipped_no_transcript_segments"
    assert result.point_count == 0


def test_invalid_segments_do_not_crash() -> None:
    result = classify_interactions([None, {"text": ""}])

    assert result.status == "completed_with_warnings"
    assert result.segment_classification_count == 2


def test_interaction_foundation_files_have_no_bom() -> None:
    for relative_path in [
        "models/interaction_classification.py",
        "core/interaction_classifier.py",
        "tests/test_interaction_classification_foundation_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_interaction_foundation_files_end_with_newline() -> None:
    for relative_path in [
        "models/interaction_classification.py",
        "core/interaction_classifier.py",
        "tests/test_interaction_classification_foundation_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
