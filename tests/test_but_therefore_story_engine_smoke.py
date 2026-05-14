from __future__ import annotations

from core.but_therefore_story_engine import ButThereforeStoryEngine
from models.but_therefore_story import (
    STORY_ROLE_AND,
    STORY_ROLE_BUT,
    STORY_ROLE_CENSOR_REVIEW,
    STORY_ROLE_CONTINUITY_BLOCKED,
    STORY_ROLE_PAYOFF,
    STORY_ROLE_PROTECTED,
    STORY_ROLE_REACTION,
    STORY_ROLE_THEREFORE,
)


def _base_job(items):
    return {
        "job_id": "job_story_engine_smoke",
        "review_timeline_plan_items": items,
    }


def _roles(report):
    return [moment.story_role for moment in report.moments]


def test_engine_builds_story_moments_from_timeline_items():
    job = _base_job(
        [
            {
                "item_id": "setup_1",
                "segment_id": "seg_setup",
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "text": "Kurzer Kontext und Plan für die Runde",
            },
            {
                "item_id": "but_1",
                "segment_id": "seg_but",
                "start_seconds": 3.0,
                "end_seconds": 7.0,
                "text": "Aber plötzlich kommt der Gegner, oh nein what",
                "hook_score": 0.90,
            },
            {
                "item_id": "therefore_1",
                "segment_id": "seg_therefore",
                "start_seconds": 7.0,
                "end_seconds": 10.0,
                "text": "Deswegen gehe ich jetzt rein und er wird killed",
            },
        ]
    )

    report = ButThereforeStoryEngine().build_report(job)

    assert report.total_moments == 3
    assert len(report.transitions) == 2
    assert report.review_required is True
    assert report.can_apply_story_changes is False
    assert report.can_remove_and_moments is False
    assert report.can_reorder_timeline is False
    assert report.can_trim is False
    assert report.can_extend is False
    assert report.can_render is False


def test_engine_classifies_but_therefore_reaction_payoff_and_and_moments():
    job = _base_job(
        [
            {
                "item_id": "but_1",
                "segment_id": "seg_but",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "text": "Aber plötzlich fail no way clutch problem bro",
                "hook_score": 0.95,
            },
            {
                "item_id": "therefore_1",
                "segment_id": "seg_therefore",
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "text": "Deshalb dann danach eliminated und geschafft",
            },
            {
                "item_id": "reaction_1",
                "segment_id": "seg_reaction",
                "start_seconds": 4.0,
                "end_seconds": 6.0,
                "text": "haha omg wow chat reaction shot",
                "reaction_score": 0.90,
            },
            {
                "item_id": "payoff_1",
                "segment_id": "seg_payoff",
                "start_seconds": 6.0,
                "end_seconds": 8.0,
                "text": "Victory win climax payoff final killed",
                "payoff_score": 0.92,
            },
            {
                "item_id": "and_1",
                "segment_id": "seg_and",
                "start_seconds": 8.0,
                "end_seconds": 10.0,
                "text": "Ich laufe weiter durch den Gang",
            },
        ]
    )

    report = ButThereforeStoryEngine().build_report(job)
    roles = _roles(report)

    assert STORY_ROLE_BUT in roles
    assert STORY_ROLE_THEREFORE in roles
    assert STORY_ROLE_REACTION in roles
    assert STORY_ROLE_PAYOFF in roles
    assert STORY_ROLE_AND in roles
    assert report.but_count >= 1
    assert report.therefore_count >= 1
    assert report.reaction_count >= 1
    assert report.payoff_count >= 1
    assert report.story_flow_score > 0.0


def test_engine_preserves_censor_protected_and_continuity_blocked_items():
    job = _base_job(
        [
            {
                "item_id": "censor_1",
                "segment_id": "seg_censor",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "action": "censor_keep",
                "text": "censor review needed",
            },
            {
                "item_id": "protected_1",
                "segment_id": "seg_protected",
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "action": "protect",
                "protected": True,
                "text": "protected context",
            },
            {
                "item_id": "continuity_1",
                "segment_id": "seg_continuity",
                "start_seconds": 4.0,
                "end_seconds": 6.0,
                "action": "blocked_by_continuity",
                "continuity_blocked": True,
                "text": "continuity blocked",
            },
        ]
    )

    report = ButThereforeStoryEngine().build_report(job)
    roles = _roles(report)

    assert STORY_ROLE_CENSOR_REVIEW in roles
    assert STORY_ROLE_PROTECTED in roles
    assert STORY_ROLE_CONTINUITY_BLOCKED in roles
    assert any(
        suggestion["suggestion_type"] == "censor_story_review_required"
        for suggestion in report.suggestions
    )
    assert any(
        suggestion["suggestion_type"] == "protected_story_preserved"
        for suggestion in report.suggestions
    )
    assert any(
        suggestion["suggestion_type"] == "continuity_story_blocked"
        for suggestion in report.suggestions
    )


def test_engine_detects_and_streak_orphan_reaction_missing_payoff_and_weak_ratio():
    job = _base_job(
        [
            {
                "item_id": "reaction_orphan",
                "segment_id": "seg_reaction",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "text": "haha omg wow reaction shot",
                "reaction_score": 0.88,
            },
            {
                "item_id": "and_1",
                "segment_id": "seg_and_1",
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "text": "Ich laufe weiter",
            },
            {
                "item_id": "and_2",
                "segment_id": "seg_and_2",
                "start_seconds": 4.0,
                "end_seconds": 6.0,
                "text": "Ich sammle kurz etwas ein",
            },
            {
                "item_id": "and_3",
                "segment_id": "seg_and_3",
                "start_seconds": 6.0,
                "end_seconds": 8.0,
                "text": "Ich gehe dann weiter",
            },
            {
                "item_id": "but_no_payoff",
                "segment_id": "seg_but_no_payoff",
                "start_seconds": 8.0,
                "end_seconds": 10.0,
                "text": "Aber plötzlich gibt es ein Problem fail",
            },
            {
                "item_id": "and_4",
                "segment_id": "seg_and_4",
                "start_seconds": 10.0,
                "end_seconds": 12.0,
                "text": "Ich laufe einfach weiter",
            },
        ]
    )

    report = ButThereforeStoryEngine().build_report(job)
    suggestion_types = {item["suggestion_type"] for item in report.suggestions}

    assert report.and_streak_max >= 3
    assert report.orphan_reaction_count >= 1
    assert report.missing_payoff_count >= 1
    assert report.but_therefore_ratio < 0.60

    assert "too_many_and_moments" in suggestion_types
    assert "orphan_reaction" in suggestion_types
    assert "missing_payoff" in suggestion_types
    assert "weak_but_therefore_ratio" in suggestion_types
