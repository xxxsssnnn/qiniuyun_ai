import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.glossary import GlossaryItem
from app.services.glossary import GlossaryConflictError, GlossaryManager


class GlossaryManagerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = GlossaryManager()

    def test_apply_glossary_is_case_insensitive_and_respects_word_boundaries(self) -> None:
        self.manager.add_entry("OpenAI", "开放人工智能")

        result = self.manager.apply_glossary("OPENAI works with openair tools.")

        self.assertEqual(result, "开放人工智能 works with openair tools.")

    def test_longer_terms_are_replaced_before_shorter_terms(self) -> None:
        self.manager.add_entry("AI", "人工智能")
        self.manager.add_entry("AI agent", "智能体")

        result = self.manager.apply_glossary("An AI agent uses AI.")

        self.assertEqual(result, "An 智能体 uses 人工智能.")

    def test_prompt_contains_only_terms_used_by_current_text(self) -> None:
        self.manager.add_entry("WebSocket", "WebSocket 协议", "保持英文产品名")
        self.manager.add_entry("Kubernetes", "Kubernetes")

        prompt = self.manager.format_prompt("Use websocket for realtime events.")

        self.assertIn("websocket => WebSocket 协议", prompt)
        self.assertIn("保持英文产品名", prompt)
        self.assertNotIn("kubernetes", prompt)


class GlossaryDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.manager = GlossaryManager()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_rename_updates_database_and_memory_together(self) -> None:
        with Session(self.engine) as session:
            self.manager.add_entry_db(session, "open ai", "OpenAI")
            renamed = self.manager.rename_entry_db(
                session,
                "open ai",
                "OpenAI API",
                "OpenAI 接口",
                "产品接口名称",
            )

            stored = session.query(GlossaryItem).one()

        self.assertIsNotNone(renamed)
        self.assertEqual(stored.source, "openai api")
        self.assertIsNone(self.manager.get_entry("open ai"))
        self.assertEqual(
            self.manager.get_entry("OPENAI API").target,
            "OpenAI 接口",
        )

    def test_rename_rejects_duplicate_without_deleting_original(self) -> None:
        with Session(self.engine) as session:
            self.manager.add_entry_db(session, "OpenAI", "开放人工智能")
            self.manager.add_entry_db(session, "ChatGPT", "聊天助手")

            with self.assertRaises(GlossaryConflictError):
                self.manager.rename_entry_db(
                    session,
                    "OpenAI",
                    "ChatGPT",
                    "新译法",
                )

            sources = {
                item.source
                for item in session.query(GlossaryItem).all()
            }

        self.assertEqual(sources, {"openai", "chatgpt"})
        self.assertEqual(self.manager.get_entry("OpenAI").target, "开放人工智能")


if __name__ == "__main__":
    unittest.main()
