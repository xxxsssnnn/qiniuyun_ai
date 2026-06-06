from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class GlossaryItem(Base):
    __tablename__ = "glossary_items"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), unique=True, nullable=False, index=True)
    target = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
