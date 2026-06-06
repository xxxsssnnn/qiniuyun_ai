from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_config import AppConfig


class ConfigStore:
    def get(self, session: Session, key: str, default: str = '') -> str:
        item = session.scalar(select(AppConfig).where(AppConfig.key == key))
        return item.value if item else default

    def set(self, session: Session, key: str, value: str) -> str:
        item = session.scalar(select(AppConfig).where(AppConfig.key == key))
        if item:
            item.value = value
        else:
            item = AppConfig(key=key, value=value)
            session.add(item)
        session.commit()
        return value

    def all(self, session: Session) -> dict[str, str]:
        items = session.scalars(select(AppConfig)).all()
        return {item.key: item.value for item in items}


config_store = ConfigStore()
