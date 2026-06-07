import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.transcript import TranscriptRecord  # noqa: F401
from app.models.transcript_session import TranscriptSession  # noqa: F401
from app.services.streaming import TranscriptChunk
from app.services.transcript_store import TranscriptStore


class TranscriptStoreSessionTestCase(unittest.TestCase):
    def test_empty_session_is_listed_before_any_subtitles_exist(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        test_session_local = sessionmaker(bind=engine)
        store = TranscriptStore()
        with patch(
            "app.services.transcript_store.SessionLocal",
            test_session_local,
        ):
            created = store.create_session("session-test", "技术分享")
            sessions = store.list_sessions()

        self.assertEqual(created.session_id, "session-test")
        self.assertEqual(created.name, "技术分享")
        self.assertEqual(created.chunk_count, 0)
        self.assertEqual([item.session_id for item in sessions], ["session-test"])

    def test_subtitles_are_isolated_between_sessions(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        test_session_local = sessionmaker(bind=engine)
        store = TranscriptStore()

        with patch(
            "app.services.transcript_store.SessionLocal",
            test_session_local,
        ):
            store.create_session("session-a", "会议 A")
            store.create_session("session-b", "会议 B")
            store.save_chunk(
                TranscriptChunk(
                    chunk_id="session-a-chunk-1",
                    session_id="session-a",
                    source_text="Hello A",
                    translated_text="你好 A",
                    is_final=True,
                )
            )
            store.save_chunk(
                TranscriptChunk(
                    chunk_id="session-b-chunk-1",
                    session_id="session-b",
                    source_text="Hello B",
                    translated_text="你好 B",
                    is_final=True,
                )
            )
            session_a_chunks = store.list_chunks("session-a")
            session_b_chunks = store.list_chunks("session-b")

        self.assertEqual(
            [chunk.source_text for chunk in session_a_chunks],
            ["Hello A"],
        )
        self.assertEqual(
            [chunk.source_text for chunk in session_b_chunks],
            ["Hello B"],
        )

    def test_each_subtitle_revision_is_preserved(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        test_session_local = sessionmaker(bind=engine)
        store = TranscriptStore()

        with patch(
            "app.services.transcript_store.SessionLocal",
            test_session_local,
        ):
            store.save_chunk(
                TranscriptChunk(
                    chunk_id="chunk-1",
                    session_id="session-a",
                    source_text="We use cash.",
                    translated_text="我们使用现金。",
                    is_final=True,
                    revision=1,
                )
            )
            store.save_chunk(
                TranscriptChunk(
                    chunk_id="chunk-1",
                    session_id="session-a",
                    source_text="We use cache.",
                    translated_text="我们使用缓存。",
                    direct_translation="我们使用现金。",
                    is_final=True,
                    revision=2,
                    auto_correction=True,
                    correction_reasons=["千问上下文复核"],
                )
            )
            history = store.list_revisions("session-a", "chunk-1")

        self.assertEqual([item.revision for item in history], [2, 1])
        self.assertEqual(history[0].source_text, "We use cache.")
        self.assertEqual(history[0].direct_translation, "我们使用现金。")
        self.assertEqual(history[1].source_text, "We use cash.")


if __name__ == "__main__":
    unittest.main()
