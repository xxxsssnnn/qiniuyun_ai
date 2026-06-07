from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from app.services.glossary import glossary_manager
from app.services.streaming import TranscriptChunk


@dataclass
class QwenCorrection:
    chunk_id: str
    source_text: str
    translated_text: str
    reason: str


class QwenSubtitleCorrectionService:
    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model = os.getenv("QWEN_CORRECTION_MODEL", "qwen3.5-flash")
        self.base_url = os.getenv(
            "QWEN_CORRECTION_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/")
        self.timeout_seconds = float(os.getenv("QWEN_CORRECTION_TIMEOUT_SECONDS", "8"))
        self.max_context_chunks = max(
            2,
            min(int(os.getenv("QWEN_CORRECTION_CONTEXT_CHUNKS", "5")), 10),
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def review(self, chunks: list[TranscriptChunk]) -> list[QwenCorrection]:
        if not self.available or len(chunks) < 2:
            return []

        review_chunks = chunks[-self.max_context_chunks :]
        allowed_ids = {chunk.chunk_id for chunk in review_chunks}
        glossary_text = glossary_manager.format_prompt(
            "\n".join(chunk.source_text for chunk in review_chunks)
        ) or "无"
        subtitle_text = "\n".join(
            json.dumps(
                {
                    "chunk_id": chunk.chunk_id,
                    "source_text": chunk.source_text,
                    "translated_text": chunk.translated_text,
                },
                ensure_ascii=False,
            )
            for chunk in review_chunks
        )
        prompt = (
            "请复核以下按时间顺序排列的实时同传字幕。利用后文纠正前文中的明显语音识别"
            "错误、上下文歧义、专有名词错误和中文翻译错误。\n"
            "要求：\n"
            "1. 只修正确实存在错误的字幕，不要润色正确内容。\n"
            "2. chunk_id 必须原样取自输入，禁止新增、删除或合并字幕。\n"
            "3. source_text 保持原语言，translated_text 保持中文。\n"
            "4. 保留数字、人名、产品名、代码和 API 名称。\n"
            "5. 没有需要修正的内容时返回空数组。\n"
            "6. 输出 JSON 对象，格式为 "
            '{"corrections":[{"chunk_id":"...","source_text":"...",'
            '"translated_text":"...","reason":"简短中文原因"}]}。\n\n'
            f"术语表：\n{glossary_text}\n\n"
            f"字幕：\n{subtitle_text}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是严谨的实时同传字幕校对器，只输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "enable_thinking": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = self._parse_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return []

        corrections: list[QwenCorrection] = []
        for item in parsed.get("corrections", []):
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id", "")).strip()
            source_text = str(item.get("source_text", "")).strip()
            translated_text = str(item.get("translated_text", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if (
                chunk_id not in allowed_ids
                or not source_text
                or not translated_text
                or not reason
            ):
                continue
            corrections.append(
                QwenCorrection(
                    chunk_id=chunk_id,
                    source_text=source_text,
                    translated_text=translated_text,
                    reason=reason,
                )
            )
        return corrections

    def _parse_json(self, content: str) -> dict:
        normalized = content.strip()
        if normalized.startswith("```"):
            normalized = re.sub(r"^```(?:json)?\s*", "", normalized)
            normalized = re.sub(r"\s*```$", "", normalized)
        parsed = json.loads(normalized)
        return parsed if isinstance(parsed, dict) else {}


qwen_correction_service = QwenSubtitleCorrectionService()
