import re
from collections import Counter
from typing import Any, Iterable, Optional

from models.hook_keyword_result import HookKeywordResult, HookSentence
from models.transcript_result import TranscriptResult, TranscriptSegment


class HookKeywordExtractor:
    engine = "rule-based-hook-keyword-v1"

    STRONG_TERMS = {
        "krass", "krasseste", "unfassbar", "heftig", "eskaliert",
        "save", "clutch", "comeback", "finale", "sieg", "gewonnen",
        "verloren", "verliere", "verlor", "lebens", "letzte",
        "wahnsinn", "verrueckt", "verrückt", "boss", "ace",
        "unglaublich", "perfekt", "schock", "extrem",
    }

    STAKES_TERMS = {
        "verloren", "gewonnen", "sieg", "finale", "letzte",
        "leben", "lebens", "comeback", "clutch", "save",
    }

    WEAK_FILLER_TERMS = {
        "okay", "ja", "dann", "hier", "mal", "weiter",
        "schauen", "laufen", "also", "halt", "einfach",
    }

    STOPWORDS = {
        "der", "die", "das", "und", "oder", "aber", "ich", "du",
        "er", "sie", "wir", "ihr", "ist", "war", "bin", "bist",
        "sind", "seid", "ein", "eine", "einer", "einen", "einem",
        "mit", "auf", "für", "von", "im", "im", "in", "am", "an",
        "zu", "zum", "zur", "den", "dem", "des", "dass", "diese",
        "dieser", "dieses", "mein", "meine", "meines", "wirklich",
        "dachte", "geht", "ging", "haben", "hat", "hatte",
    }

    def analyze(
        self,
        source: Any = None,
        *,
        text: Optional[str] = None,
        segments: Optional[Iterable[Any]] = None,
        max_keywords: int = 8,
        max_hooks: int = 5,
        min_top_hook_score: float = 0.55,
    ) -> HookKeywordResult:
        transcript_segments = self._resolve_segments(source=source, segments=segments)

        if transcript_segments:
            full_text = " ".join(
                segment.text.strip()
                for segment in transcript_segments
                if segment.text.strip()
            ).strip()
            hook_units = transcript_segments
        else:
            full_text = str(text if text is not None else source or "").strip()
            hook_units = [
                TranscriptSegment(
                    start_seconds=None,
                    end_seconds=None,
                    text=sentence,
                    confidence=None,
                )
                for sentence in self._split_sentences(full_text)
            ]

        if not full_text:
            return HookKeywordResult(
                keywords=[],
                hook_sentences=[],
                top_hook=None,
                engine=self.engine,
                source_text_length=0,
            )

        keywords = self._extract_keywords(full_text, max_keywords=max_keywords)

        hook_sentences = [
            self._score_hook_sentence(unit)
            for unit in hook_units
            if str(unit.text or "").strip()
        ]

        hook_sentences.sort(key=lambda item: item.score, reverse=True)
        hook_sentences = hook_sentences[:max_hooks]

        top_hook = None
        if hook_sentences and hook_sentences[0].score >= min_top_hook_score:
            top_hook = hook_sentences[0].text

        return HookKeywordResult(
            keywords=keywords,
            hook_sentences=hook_sentences,
            top_hook=top_hook,
            engine=self.engine,
            source_text_length=len(full_text),
        )

    def _resolve_segments(
        self,
        source: Any,
        segments: Optional[Iterable[Any]],
    ) -> list[TranscriptSegment]:
        raw_segments = None

        if segments is not None:
            raw_segments = segments
        elif isinstance(source, TranscriptResult):
            raw_segments = source.segments
        elif isinstance(source, list):
            raw_segments = source

        if raw_segments is None:
            return []

        resolved = []
        for item in raw_segments:
            segment_text = getattr(item, "text", None)
            start_seconds = getattr(item, "start_seconds", None)
            end_seconds = getattr(item, "end_seconds", None)
            confidence = getattr(item, "confidence", None)

            if isinstance(item, dict):
                segment_text = item.get("text")
                start_seconds = item.get("start_seconds")
                end_seconds = item.get("end_seconds")
                confidence = item.get("confidence")

            clean_text = str(segment_text or "").strip()
            if not clean_text:
                continue

            resolved.append(
                TranscriptSegment(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    text=clean_text,
                    confidence=confidence,
                )
            )

        return resolved

    def _split_sentences(self, text: str) -> list[str]:
        clean_text = str(text or "").strip()
        if not clean_text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", clean_text)
        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    def _extract_keywords(self, text: str, max_keywords: int) -> list[str]:
        tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", text)
        ]

        cleaned_tokens = [
            token
            for token in tokens
            if len(token) >= 3 and token not in self.STOPWORDS
        ]

        counts = Counter(cleaned_tokens)
        first_position = {}

        for index, token in enumerate(cleaned_tokens):
            if token not in first_position:
                first_position[token] = index

        ranked = sorted(
            counts.keys(),
            key=lambda token: (
                -(counts[token] + self._keyword_bonus(token)),
                first_position[token],
                token,
            ),
        )

        return ranked[:max_keywords]

    def _keyword_bonus(self, token: str) -> float:
        bonus = 0.0

        if token in self.STRONG_TERMS:
            bonus += 3.0

        if token in self.STAKES_TERMS:
            bonus += 1.0

        if len(token) >= 8:
            bonus += 0.25

        return bonus

    def _score_hook_sentence(self, segment: TranscriptSegment) -> HookSentence:
        text = str(segment.text or "").strip()
        lowered = text.lower()
        tokens = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", lowered)

        score = 0.20
        reasons = []

        strong_hits = [
            token
            for token in tokens
            if token in self.STRONG_TERMS
        ]

        stakes_hits = [
            token
            for token in tokens
            if token in self.STAKES_TERMS
        ]

        filler_hits = [
            token
            for token in tokens
            if token in self.WEAK_FILLER_TERMS
        ]

        if strong_hits:
            bonus = min(0.36, len(set(strong_hits)) * 0.12)
            score += bonus
            reasons.append("strong_words")

        if stakes_hits:
            score += 0.14
            reasons.append("stakes")

        if "!" in text:
            score += 0.08
            reasons.append("exclamation")

        if "?" in text:
            score += 0.07
            reasons.append("question")

        if "ich dachte" in lowered or "meines lebens" in lowered:
            score += 0.16
            reasons.append("personal_tension")

        if any(word in lowered for word in ["krasseste", "beste", "schlimmste", "letzte"]):
            score += 0.10
            reasons.append("superlative")

        token_count = len(tokens)
        if 5 <= token_count <= 22:
            score += 0.10
            reasons.append("good_hook_length")
        elif token_count > 35:
            score -= 0.10
            reasons.append("too_long")

        if filler_hits and not strong_hits and not stakes_hits:
            score -= 0.18
            reasons.append("weak_filler")

        score = round(max(0.0, min(1.0, score)), 3)

        if not reasons:
            reasons.append("neutral_text")

        return HookSentence(
            text=text,
            score=score,
            reason=",".join(reasons),
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
        )
