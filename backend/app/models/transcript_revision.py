from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class TranscriptRevision(Base):
    __tablename__ = "transcript_revisions"
    __table_args__ = (
        UniqueConstraint("chunk_id", "revision", name="uq_chunk_revision"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    chunk_id = Column(String(128), nullable=False, index=True)
    source_text = Column(Text, nullable=False, default="")
    translated_text = Column(Text, nullable=False, default="")
    is_final = Column(Boolean, nullable=False, default=True)
    revision = Column(Integer, nullable=False, default=0)
    auto_correction = Column(Boolean, nullable=False, default=False)
    correction_reasons = Column(Text, nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
