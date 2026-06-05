from typing import Optional

from pydantic import BaseModel, Field


class TranscriptChunkCreate(BaseModel):
    chunk_id: str = Field(..., description="Chunk identifier")
    source_text: str = Field(..., description="Original transcript text")
    translated_text: Optional[str] = Field(default=None, description="Translated Chinese text")
    is_final: bool = Field(default=False, description="Whether the chunk is final")


class TranscriptChunkRead(BaseModel):
    chunk_id: str
    source_text: str
    translated_text: str = ""
    is_final: bool = False
