from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class TranscriptRecord(Base):
    __tablename__ = "transcript_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    chunk_id = Column(String(128), nullable=False, unique=True, index=True)
    source_text = Column(Text, nullable=False, default="")
    translated_text = Column(Text, nullable=False, default="")
    direct_translation = Column(Text, nullable=False, default="")
    is_final = Column(Boolean, nullable=False, default=False)
    revision = Column(Integer, nullable=False, default=0)
    auto_correction = Column(Boolean, nullable=False, default=False)
    correction_reasons = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
