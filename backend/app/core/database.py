from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_transcript_translation_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    for table_name in ("transcript_records", "transcript_revisions"):
        if table_name not in table_names:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "direct_translation" in columns:
            continue
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN direct_translation TEXT NOT NULL DEFAULT ''"
                )
            )
            connection.execute(
                text(
                    f"UPDATE {table_name} "
                    "SET direct_translation = translated_text "
                    "WHERE direct_translation = ''"
                )
            )
    if {"transcript_records", "transcript_revisions"} <= table_names:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE transcript_revisions "
                    "SET direct_translation = ("
                    "SELECT original.translated_text "
                    "FROM transcript_revisions AS original "
                    "WHERE original.chunk_id = transcript_revisions.chunk_id "
                    "ORDER BY original.revision ASC, original.id ASC LIMIT 1"
                    ")"
                )
            )
            connection.execute(
                text(
                    "UPDATE transcript_records "
                    "SET direct_translation = COALESCE(("
                    "SELECT original.translated_text "
                    "FROM transcript_revisions AS original "
                    "WHERE original.chunk_id = transcript_records.chunk_id "
                    "ORDER BY original.revision ASC, original.id ASC LIMIT 1"
                    "), translated_text)"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
