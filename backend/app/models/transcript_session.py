from sqlalchemy import Column, DateTime, String, func

from app.core.database import Base


class TranscriptSession(Base):
    __tablename__ = "transcript_sessions"

    session_id = Column(String(128), primary_key=True)
    name = Column(String(160), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
