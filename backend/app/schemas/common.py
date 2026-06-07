from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptChunkCreate(BaseModel):
    chunk_id: str = Field(..., description="Chunk identifier")
    source_text: str = Field(..., description="Original transcript text")
    translated_text: Optional[str] = Field(default=None, description="Translated Chinese text")
    is_final: bool = Field(default=False, description="Whether the chunk is final")


class TranscriptChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    source_text: str
    translated_text: str = ""
    is_final: bool = False
    session_id: str = "default"
    revision: int = 0
    auto_correction: bool = False
    correction_reasons: list[str] = Field(default_factory=list)
