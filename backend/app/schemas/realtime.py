from pydantic import BaseModel, Field


class StreamSessionCreate(BaseModel):
    session_id: str = Field(..., description="Streaming session identifier")
    source_language: str = Field(default="en", description="Original speech language")
    target_language: str = Field(default="zh", description="Target translation language")


class StreamSessionState(BaseModel):
    session_id: str
    source_language: str
    target_language: str
    is_active: bool = True


class StreamTextChunk(BaseModel):
    chunk_id: str
    session_id: str
    source_text: str
    translated_text: str = ""
    is_final: bool = False
    start_ms: int | None = None
    end_ms: int | None = None
    revision: int = 0


class AudioChunkMessage(BaseModel):
    type: str = "audio"
    session_id: str
    mime_type: str = "audio/webm;codecs=opus"
    data_base64: str
