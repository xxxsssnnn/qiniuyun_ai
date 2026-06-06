from sqlalchemy import Column, Integer, String

from app.core.database import Base


class AppConfig(Base):
    __tablename__ = 'app_configs'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(String(512), nullable=False)
