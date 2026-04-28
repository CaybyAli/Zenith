from __future__ import annotations

from dataclasses import dataclass

from models.job import Job


def clamp_score(value: float | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, min(10.0, float(value))), 1)


@dataclass(slots=True, frozen=True)
class ScoreResult:
    quality_score: float | None = None
    hook_score: float | None = None
    editing_score: float | None = None
    retention_potential_score: float | None = None
    shorts_potential_score: float | None = None
    final_score: float | None = None
    decision_reason: str | None = None
    improvement_hint: str | None = None
    recommended_action: str | None = None


def calculate_final_score(
    quality_score: float | None,
    hook_score: float | None,
    editing_score: float | None,
    retention_potential_score: float | None,
    shorts_potential_score: float | None,
) -> float | None:
    weighted_scores: list[tuple[float, float]] = []

    if quality_score is not None:
        weighted_scores.append((quality_score, 0.30))
    if hook_score is not None:
        weighted_scores.append((hook_score, 0.20))
    if editing_score is not None:
        weighted_scores.append((editing_score, 0.20))
    if retention_potential_score is not None:
        weighted_scores.append((retention_potential_score, 0.20))
    if shorts_potential_score is not None:
        weighted_scores.append((shorts_potential_score, 0.10))

    if not weighted_scores:
        return None

    total_weight = sum(weight for _, weight in weighted_scores)
    total_value = sum(score * weight for score, weight in weighted_scores)

    return round(total_value / total_weight, 1)


def derive_recommended_action(
    final_score: float | None,
    quality_score: float | None,
    hook_score: float | None,
) -> str:
    if final_score is None:
        return "manual_review"

    if final_score >= 8.0 and (quality_score or 0.0) >= 7.0 and (hook_score or 0.0) >= 6.5:
        return "approve_candidate"

    if final_score >= 6.0:
        return "manual_review"

    return "reject_candidate"


def derive_decision_reason(
    final_score: float | None,
    quality_score: float | None,
    hook_score: float | None,
    editing_score: float | None,
) -> str:
    if final_score is None:
        return "keine ausreichenden Score-Daten"

    if final_score >= 8.0 and (quality_score or 0.0) >= 7.0 and (hook_score or 0.0) >= 6.5:
        return "starke Gesamtwirkung, solide Qualität und brauchbarer Hook"

    if final_score >= 6.0:
        if (hook_score or 0.0) < 6.5:
            return "solide Basis, aber Hook noch nicht stark genug"
        if (quality_score or 0.0) < 7.0:
            return "brauchbarer Ansatz, aber Gesamtqualität noch ausbaufähig"
        return "solide Gesamtleistung, manuelle Prüfung sinnvoll"

    if (editing_score or 0.0) < 5.5:
        return "schwache Gesamtwirkung und Editing aktuell zu schwach"

    return "schwache Gesamtwirkung, aktuell keine Freigabe empfohlen"


def derive_improvement_hint(
    quality_score: float | None,
    hook_score: float | None,
    editing_score: float | None,
    final_score: float | None,
) -> str:
    if final_score is None:
        return "mehr Bewertungsdaten sammeln"

    if (hook_score or 0.0) < 6.5:
        return "erste 3 Sekunden stärker machen"

    if (quality_score or 0.0) < 7.0:
        return "Bild und Audioqualität weiter verbessern"

    if (editing_score or 0.0) < 6.5:
        return "Schnitt dynamischer und präziser machen"

    if final_score >= 8.0:
        return "kleine Optimierungen testen und Struktur beibehalten"

    return "Hook und Tempo noch etwas schärfer ausarbeiten"


def build_score_result(
    quality_score: float | None = None,
    hook_score: float | None = None,
    editing_score: float | None = None,
    retention_potential_score: float | None = None,
    shorts_potential_score: float | None = None,
    decision_reason: str | None = None,
    improvement_hint: str | None = None,
    recommended_action: str | None = None,
) -> ScoreResult:
    quality_score = clamp_score(quality_score)
    hook_score = clamp_score(hook_score)
    editing_score = clamp_score(editing_score)
    retention_potential_score = clamp_score(retention_potential_score)
    shorts_potential_score = clamp_score(shorts_potential_score)

    final_score = calculate_final_score(
        quality_score=quality_score,
        hook_score=hook_score,
        editing_score=editing_score,
        retention_potential_score=retention_potential_score,
        shorts_potential_score=shorts_potential_score,
    )

    if recommended_action is None:
        recommended_action = derive_recommended_action(
            final_score=final_score,
            quality_score=quality_score,
            hook_score=hook_score,
        )

    if decision_reason is None:
        decision_reason = derive_decision_reason(
            final_score=final_score,
            quality_score=quality_score,
            hook_score=hook_score,
            editing_score=editing_score,
        )

    if improvement_hint is None:
        improvement_hint = derive_improvement_hint(
            quality_score=quality_score,
            hook_score=hook_score,
            editing_score=editing_score,
            final_score=final_score,
        )

    return ScoreResult(
        quality_score=quality_score,
        hook_score=hook_score,
        editing_score=editing_score,
        retention_potential_score=retention_potential_score,
        shorts_potential_score=shorts_potential_score,
        final_score=final_score,
        decision_reason=decision_reason,
        improvement_hint=improvement_hint,
        recommended_action=recommended_action,
    )


def apply_score_result_to_job(job: Job, score_result: ScoreResult) -> Job:
    job.quality_score = score_result.quality_score
    job.hook_score = score_result.hook_score
    job.editing_score = score_result.editing_score
    job.retention_potential_score = score_result.retention_potential_score
    job.shorts_potential_score = score_result.shorts_potential_score
    job.final_score = score_result.final_score
    job.decision_reason = score_result.decision_reason
    job.improvement_hint = score_result.improvement_hint
    job.recommended_action = score_result.recommended_action
    job.touch()
    return job



def score_job_with_inputs(
    job: Job,
    quality_score: float | None = None,
    hook_score: float | None = None,
    editing_score: float | None = None,
    retention_potential_score: float | None = None,
    shorts_potential_score: float | None = None,
    decision_reason: str | None = None,
    improvement_hint: str | None = None,
    recommended_action: str | None = None,
) -> Job:
    score_result = build_score_result(
        quality_score=quality_score,
        hook_score=hook_score,
        editing_score=editing_score,
        retention_potential_score=retention_potential_score,
        shorts_potential_score=shorts_potential_score,
        decision_reason=decision_reason,
        improvement_hint=improvement_hint,
        recommended_action=recommended_action,
    )

    return apply_score_result_to_job(job, score_result)