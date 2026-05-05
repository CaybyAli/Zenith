from __future__ import annotations

import re
import uuid
from typing import Any

from models.sentence_timeline import SentenceItem, SentenceTimelineResult


class SentenceTimelineBuilder:
    engine = "sentence-timeline-builder-v1"

    FILLER_TERMS = {
        "aeh",
        "aehm",
        "äh",
        "ähm",
        "okay",
        "ja",
        "so",
        "also",
        "keine ahnung",
        "warte",
        "digga",
        "bro",
    }
    QUESTION_STARTS = {"warum", "wie", "was", "wer", "wann", "wo", "hä", "hae"}
    EXCLAMATION_TERMS = {
        "krass",
        "alter",
        "no way",
        "wtf",
        "oh mein gott",
        "junge",
        "was war das",
    }
    HOOK_TERMS = {
        "clutch",
        "save",
        "letzte sekunde",
        "unmöglich",
        "unmoeglich",
        "komplett tot",
        "verloren",
        "gewonnen",
        "challenge",
        "fehler",
        "rettung",
        "nils",
        "niemals",
        "wichtigste",
        "krasseste",
    }
    INCOMPLETE_ENDINGS = {"und", "aber", "weil", "dann", "wenn", "dass", "also"}

    def _make_sentence_id(self) -> str:
        return f"sentence_{uuid.uuid4().hex[:12]}"

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        return round(max(0.0, min(1.0, self._safe_float(value, fallback))), 3)

    def _segment_rows(self, transcript_result: object) -> list[dict[str, Any]]:
        segments = getattr(transcript_result, "segments", None)
        if isinstance(transcript_result, dict):
            segments = transcript_result.get("segments")
        if not segments:
            return []

        rows: list[dict[str, Any]] = []
        for index, segment in enumerate(segments):
            if isinstance(segment, dict):
                text = segment.get("text")
                start = segment.get("start_seconds")
                end = segment.get("end_seconds")
                confidence = segment.get("confidence")
            else:
                text = getattr(segment, "text", None)
                start = getattr(segment, "start_seconds", None)
                end = getattr(segment, "end_seconds", None)
                confidence = getattr(segment, "confidence", None)

            clean_text = " ".join(str(text or "").strip().split())
            if not clean_text:
                continue

            start_seconds = max(0.0, self._safe_float(start, 0.0))
            end_seconds = max(start_seconds, self._safe_float(end, start_seconds))
            if end_seconds <= start_seconds:
                continue

            rows.append(
                {
                    "segment_id": f"segment_{index:06d}",
                    "text": clean_text,
                    "start_seconds": round(start_seconds, 3),
                    "end_seconds": round(end_seconds, 3),
                    "confidence": confidence,
                }
            )

        return sorted(rows, key=lambda row: (row["start_seconds"], row["end_seconds"]))

    def _has_sentence_punctuation(self, text: str) -> bool:
        return bool(re.search(r"[.!?…]\s*$", text.strip()) or re.search(r"[.!?…]", text))

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", text.lower())

    def _matched_terms(self, lowered: str, terms: set[str]) -> list[str]:
        return sorted(term for term in terms if term in lowered)

    def _classify(self, text: str, ended_by: str) -> tuple[str, float, dict[str, Any]]:
        clean_text = " ".join(text.strip().split())
        lowered = clean_text.lower()
        words = self._words(clean_text)
        word_count = len(words)
        has_question_mark = "?" in clean_text
        has_exclamation_mark = "!" in clean_text

        hook_hits = self._matched_terms(lowered, self.HOOK_TERMS)
        exclamation_hits = self._matched_terms(lowered, self.EXCLAMATION_TERMS)
        filler_hits = self._matched_terms(lowered, self.FILLER_TERMS)
        starts_question = bool(words and words[0] in self.QUESTION_STARTS)
        last_word = words[-1] if words else ""
        has_punctuation_end = bool(re.search(r"[.!?…]\s*$", clean_text))

        filler_ratio = len(set(filler_hits)) / max(1, word_count)
        is_short_filler = word_count <= 3 and not has_question_mark and not has_exclamation_mark
        is_many_fillers = bool(filler_hits) and (filler_ratio >= 0.34 or word_count <= 4)
        is_incomplete = (
            (not has_punctuation_end and last_word in self.INCOMPLETE_ENDINGS)
            or (
                not has_punctuation_end
                and word_count <= 4
                and ended_by != "punctuation"
                and not is_many_fillers
            )
        )

        matched_terms: list[str] = []
        if hook_hits:
            sentence_kind = "hook"
            score = 0.68 + min(0.22, len(hook_hits) * 0.06)
            if has_exclamation_mark:
                score += 0.05
            matched_terms = hook_hits
        elif has_exclamation_mark or exclamation_hits:
            sentence_kind = "exclamation"
            score = 0.58 + min(0.17, len(exclamation_hits) * 0.05)
            matched_terms = exclamation_hits
        elif has_question_mark or starts_question:
            sentence_kind = "question"
            score = 0.50 if has_question_mark else 0.45
            matched_terms = [words[0]] if starts_question and words else []
        elif is_incomplete:
            sentence_kind = "incomplete"
            score = 0.28 if word_count <= 4 else 0.38
            matched_terms = [last_word] if last_word else []
        elif is_short_filler or is_many_fillers:
            sentence_kind = "filler"
            score = 0.18 if word_count <= 3 else 0.26
            matched_terms = filler_hits
        else:
            sentence_kind = "normal"
            score = 0.42
            if 6 <= word_count <= 22:
                score += 0.08
            if word_count > 28:
                score -= 0.05

        metadata = {
            "word_count": word_count,
            "has_question_mark": has_question_mark,
            "has_exclamation_mark": has_exclamation_mark,
            "matched_terms": matched_terms,
            "ended_by": ended_by,
        }
        return sentence_kind, self._clamp(score), metadata

    def _flush_sentence(
        self,
        rows: list[dict[str, Any]],
        ended_by: str,
    ) -> SentenceItem | None:
        if not rows:
            return None

        text = " ".join(row["text"] for row in rows).strip()
        if not text:
            return None

        confidences = [
            self._clamp(row["confidence"], 0.75)
            for row in rows
            if row.get("confidence") is not None
        ]
        confidence = (
            round(sum(confidences) / len(confidences), 3)
            if confidences
            else 0.75
        )
        sentence_kind, score, metadata = self._classify(text, ended_by)
        source_segment_ids = [row["segment_id"] for row in rows]

        return SentenceItem(
            sentence_id=self._make_sentence_id(),
            text=text,
            start_seconds=rows[0]["start_seconds"],
            end_seconds=rows[-1]["end_seconds"],
            duration_seconds=rows[-1]["end_seconds"] - rows[0]["start_seconds"],
            score=score,
            confidence=confidence,
            sentence_kind=sentence_kind,
            speaker_role="unknown",
            source_segment_ids=source_segment_ids,
            metadata=metadata,
        )

    def build(
        self,
        transcript_result: object = None,
        *,
        max_gap_seconds: float = 0.75,
        max_sentence_duration_seconds: float = 14.0,
    ) -> SentenceTimelineResult:
        rows = self._segment_rows(transcript_result)
        if not rows:
            return SentenceTimelineResult(
                sentences=[],
                engine=self.engine,
                skipped_reason="no transcript segments",
            )

        max_gap = max(0.0, float(max_gap_seconds))
        max_duration = max(0.001, float(max_sentence_duration_seconds))
        sentences: list[SentenceItem] = []
        current_rows: list[dict[str, Any]] = []

        for index, row in enumerate(rows):
            current_rows.append(row)
            next_row = rows[index + 1] if index + 1 < len(rows) else None
            current_text = " ".join(item["text"] for item in current_rows)
            duration = current_rows[-1]["end_seconds"] - current_rows[0]["start_seconds"]

            ended_by = None
            if self._has_sentence_punctuation(row["text"]) or re.search(r"[.!?…]", current_text):
                ended_by = "punctuation"
            elif next_row is not None and next_row["start_seconds"] - row["end_seconds"] > max_gap:
                ended_by = "gap"
            elif duration >= max_duration:
                ended_by = "max_duration"
            elif next_row is None:
                ended_by = "end_of_transcript"

            if ended_by:
                sentence = self._flush_sentence(current_rows, ended_by)
                if sentence is not None:
                    sentences.append(sentence)
                current_rows = []

        return SentenceTimelineResult(
            sentences=sentences,
            engine=self.engine,
            skipped_reason="no sentences" if not sentences else None,
        )
