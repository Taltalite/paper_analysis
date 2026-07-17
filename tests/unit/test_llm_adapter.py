import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.llm.openai_compatible import (
    OpenAICompatibleLLM,
    VisionNotConfiguredError,
)
from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.adapters.parser.multimodal_figure_semantics import (
    MultimodalFigureSemanticExtractor,
)
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


class KimiLLMTest(unittest.TestCase):
    def test_kimi_api_key_uses_kimi_defaults(self) -> None:
        with patch.dict(os.environ, {"KIMI_API_KEY": "kimi-key"}, clear=True):
            client = create_llm_client_from_env()

        self.assertIsNotNone(client)
        llm = client.to_crewai_llm()
        self.assertEqual(llm.model, "kimi-k3")
        self.assertEqual(llm.base_url, "https://api.moonshot.cn/v1")

    def test_kimi_env_overrides_openai_env(self) -> None:
        env = {
            "KIMI_API_KEY": "kimi-key",
            "KIMI_MODEL": "kimi-k3-turbo",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_MODEL": "gpt-4.1-mini",
        }
        with patch.dict(os.environ, env, clear=True):
            client = create_llm_client_from_env()

        llm = client.to_crewai_llm()
        self.assertEqual(llm.model, "kimi-k3-turbo")
        self.assertEqual(llm.api_key, "kimi-key")

    def test_kimi_custom_base_url_and_temperature(self) -> None:
        env = {
            "KIMI_API_KEY": "kimi-key",
            "KIMI_BASE_URL": "https://api.moonshot.ai/v1",
            "KIMI_TEMPERATURE": "0.5",
        }
        with patch.dict(os.environ, env, clear=True):
            client = create_llm_client_from_env()

        llm = client.to_crewai_llm()
        self.assertEqual(llm.base_url, "https://api.moonshot.ai/v1")
        self.assertEqual(llm.temperature, 0.5)

    def test_kimi_requires_api_key(self) -> None:
        with patch.dict(os.environ, {"KIMI_MODEL": "kimi-k3"}, clear=True):
            with self.assertRaisesRegex(ValueError, "缺少 KIMI_API_KEY"):
                create_llm_client_from_env()

    def test_openai_fallback_unchanged_when_no_kimi_vars(self) -> None:
        env = {"OPENAI_API_KEY": "openai-key", "OPENAI_MODEL": "gpt-4.1-mini"}
        with patch.dict(os.environ, env, clear=True):
            client = create_llm_client_from_env()

        llm = client.to_crewai_llm()
        self.assertEqual(llm.model, "gpt-4.1-mini")

    def test_no_env_returns_none(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(create_llm_client_from_env())


class VisionLLMTest(unittest.TestCase):
    def test_complete_with_images_requires_vision_model(self) -> None:
        adapter = OpenAICompatibleLLM(model="kimi-k3", api_key="k", base_url="https://x/v1")
        with self.assertRaises(VisionNotConfiguredError):
            adapter.complete_with_images(prompt="p", image_paths=[])

    def test_kimi_vision_model_env(self) -> None:
        env = {"KIMI_API_KEY": "kimi-key", "KIMI_VISION_MODEL": "moonshot-v1-32k-vision-preview"}
        with patch.dict(os.environ, env, clear=True):
            client = create_llm_client_from_env()

        self.assertEqual(client.vision_model, "moonshot-v1-32k-vision-preview")

    def test_bootstrap_uses_multimodal_extractor_when_vision_configured(self) -> None:
        env = {"KIMI_API_KEY": "kimi-key", "KIMI_VISION_MODEL": "moonshot-v1-32k-vision-preview"}
        with patch.dict(os.environ, env, clear=True):
            service = build_default_analysis_service()

        extractor = service._runtime._research_paper_pipeline._figure_grounding_runner._extractor
        self.assertIsInstance(extractor, MultimodalFigureSemanticExtractor)

    def test_bootstrap_uses_noop_extractor_without_vision(self) -> None:
        with patch.dict(os.environ, {"KIMI_API_KEY": "kimi-key"}, clear=True):
            service = build_default_analysis_service()

        extractor = service._runtime._research_paper_pipeline._figure_grounding_runner._extractor
        self.assertIsInstance(extractor, NoopFigureSemanticExtractor)

    def test_complete_with_images_builds_openai_compatible_payload(self) -> None:
        adapter = OpenAICompatibleLLM(
            model="kimi-k3",
            api_key="kimi-key",
            base_url="https://api.moonshot.cn/v1/",
            vision_model="moonshot-v1-32k-vision-preview",
        )
        response = MagicMock()
        response.json.return_value = {"choices": [{"message": {"content": "图表描述"}}]}
        response.raise_for_status = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "crop.png"
            image_path.write_bytes(b"\x89PNG-fake")
            with patch("paper_analysis.adapters.llm.openai_compatible.httpx.post", return_value=response) as post:
                result = adapter.complete_with_images(prompt="描述这张图", image_paths=[image_path])

        self.assertEqual(result, "图表描述")
        endpoint = post.call_args.args[0]
        self.assertEqual(endpoint, "https://api.moonshot.cn/v1/chat/completions")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "moonshot-v1-32k-vision-preview")
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "描述这张图"})
        self.assertEqual(content[1]["type"], "image_url")
        expected_uri = "data:image/png;base64," + base64.b64encode(b"\x89PNG-fake").decode("ascii")
        self.assertEqual(content[1]["image_url"]["url"], expected_uri)
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer kimi-key")


if __name__ == "__main__":
    unittest.main()
