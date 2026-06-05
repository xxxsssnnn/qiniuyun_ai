from dataclasses import dataclass


@dataclass
class TranslationRequest:
    source_text: str
    source_language: str = "en"
    target_language: str = "zh"


class TranslationService:
    def translate(self, request: TranslationRequest) -> str:
        # 占位实现：后续替换成大模型/翻译服务调用
        return request.source_text
