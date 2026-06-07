from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.glossary import glossary_manager


@dataclass
class AutoCorrectionResult:
    source_text: str
    translated_text: str
    changed: bool = False
    reasons: list[str] = field(default_factory=list)


class AutoCorrectionEngine:
    """Lightweight realtime subtitle correction engine.

    The engine focuses on corrections that can be made safely without blocking the
    realtime pipeline for too long: ASR cleanup, repeated-word removal, glossary
    consistency checks, and low-confidence retranslation triggers.
    """

    _filler_pattern = re.compile(
        r"\b(?:um+|uh+|erm+|ah+|you know|like|actually actually)\b",
        re.IGNORECASE,
    )
    _repeated_word_pattern = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)
    _space_before_punctuation_pattern = re.compile(r"\s+([,.!?;:])")
    _multi_space_pattern = re.compile(r"\s{2,}")

    _common_asr_confusions = {
        "open a i": "OpenAI",
        "open ai": "OpenAI",
        "chat g p t": "ChatGPT",
        "chat gpt": "ChatGPT",
        "kubernetees": "Kubernetes",
        "cube er net ease": "Kubernetes",
        "type script": "TypeScript",
        "java script": "JavaScript",
        "fast api": "FastAPI",
        "web socket": "WebSocket",
    }

    def correct(
        self,
        *,
        source_text: str,
        translated_text: str,
        confidence: float,
        force_review: bool = False,
    ) -> AutoCorrectionResult:
        corrected_source = source_text.strip()
        corrected_translation = translated_text.strip()
        reasons: list[str] = []

        cleaned = self._normalize_source(corrected_source)
        if cleaned != corrected_source:
            corrected_source = cleaned
            reasons.append("清理识别噪声和重复词")

        glossary_translation = self._enforce_glossary_targets(
            corrected_source,
            corrected_translation,
        )
        if glossary_translation != corrected_translation:
            corrected_translation = glossary_translation
            reasons.append("根据术语库修正译文")

        if confidence and confidence < 0.68:
            reasons.append("低置信度片段触发二次校正")
        elif force_review:
            reasons.append("上下文更新触发二次校正")

        return AutoCorrectionResult(
            source_text=corrected_source,
            translated_text=corrected_translation,
            changed=bool(reasons),
            reasons=reasons,
        )

    def _normalize_source(self, text: str) -> str:
        result = text.strip()
        result = self._filler_pattern.sub("", result)
        for wrong, right in self._common_asr_confusions.items():
            result = re.sub(rf"\b{re.escape(wrong)}\b", right, result, flags=re.IGNORECASE)
        result = self._repeated_word_pattern.sub(lambda match: match.group(1), result)
        result = self._space_before_punctuation_pattern.sub(r"\1", result)
        result = self._multi_space_pattern.sub(" ", result)
        return result.strip()

    def _enforce_glossary_targets(self, source_text: str, translated_text: str) -> str:
        if not source_text or not translated_text:
            return translated_text

        corrected = translated_text
        for entry in glossary_manager.matching_entries(source_text):
            if entry.target and entry.target not in corrected:
                corrected = f"{corrected}（术语：{entry.source}={entry.target}）"
        return corrected


auto_correction_engine = AutoCorrectionEngine()
