from dataclasses import dataclass


@dataclass
class TranslationRequest:
    source_text: str
    source_language: str = "en"
    target_language: str = "zh"


class TranslationService:
    def translate(self, request: TranslationRequest) -> str:
        # 这里先保留占位实现，后续接入大模型或翻译模型
        return request.source_text
