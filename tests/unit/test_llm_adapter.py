import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM
from paper_analysis.env import load_project_dotenv
from paper_analysis.services.bootstrap import build_default_analysis_service


class OpenAICompatibleLLMTest(unittest.TestCase):
    def test_builds_crewai_llm(self) -> None:
        adapter = OpenAICompatibleLLM(
            model="gpt-4o-mini",
            api_key="test-key",
            base_url="https://example.com/v1",
            provider="openai",
        )

        llm = adapter.to_crewai_llm()

        self.assertEqual(llm.model, "gpt-4o-mini")

    def test_create_llm_client_from_env_requires_api_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4.1-mini"}, clear=True):
            with self.assertRaisesRegex(ValueError, "缺少 OPENAI_API_KEY"):
                create_llm_client_from_env()

    def test_build_default_analysis_service_fails_fast_without_api_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4.1-mini"}, clear=True):
            with self.assertRaisesRegex(ValueError, "缺少 OPENAI_API_KEY"):
                build_default_analysis_service()

    def test_load_project_dotenv_populates_missing_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                'OPENAI_API_KEY="test-key"\nOPENAI_MODEL="gpt-4.1-mini"\n',
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                loaded = load_project_dotenv(dotenv_path)

                self.assertTrue(loaded)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "test-key")
                self.assertEqual(os.environ["OPENAI_MODEL"], "gpt-4.1-mini")

    def test_load_project_dotenv_preserves_existing_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text('OPENAI_API_KEY="dotenv-key"\n', encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
                loaded = load_project_dotenv(dotenv_path)

                self.assertFalse(loaded)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "shell-key")


if __name__ == "__main__":
    unittest.main()
