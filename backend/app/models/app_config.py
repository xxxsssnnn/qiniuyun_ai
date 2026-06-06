from sqlalchemy import Column, Integer, String

from app.core.database import Base


class AppConfig(Base):
    __tablename__ = 'app_configs'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(String(2048), nullable=False, default='')
