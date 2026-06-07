from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class GlossaryConversionRecord(Base):
    __tablename__ = "glossary_conversions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    chunk_id = Column(String(128), nullable=False, index=True)
    glossary_source = Column(String(255), nullable=False, index=True)
    glossary_target = Column(String(255), nullable=False)
    before_text = Column(Text, nullable=False, default="")
    converted_text = Column(Text, nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
