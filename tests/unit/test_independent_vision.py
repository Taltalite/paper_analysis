"""供应商隔离、缓存隔离及报告/问答装配；全程不调用模型。"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.services.bootstrap import build_default_analysis_service
from paper_analysis.services.question_answer_service import build_question_answer_service


class IndependentVisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = {"KIMI_API_KEY": "text-secret", "KIMI_MODEL": "kimi-for-coding",
                    "KIMI_BASE_URL": "https://api.kimi.com/coding/v1",
                    "KIMI_VISION_MODEL": "old-vision", "VISION_MODEL": "qwen3-vl-plus",
                    "VISION_API_KEY": "vision-secret", "VISION_BASE_URL": "https://vision.example/v1"}

    def test_separate_credentials_endpoint_and_temperature(self) -> None:
        with patch.dict(os.environ, self.env, clear=True):
            client = create_llm_client_from_env()
        text = client.to_crewai_llm()
        self.assertEqual(text.api_key, "text-secret")
        self.assertEqual(text.base_url, self.env["KIMI_BASE_URL"])
        self.assertEqual(text.temperature, 1)
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "观察"}}]}
        with patch("paper_analysis.adapters.llm.openai_compatible.httpx.post", return_value=response) as post:
            client.complete_with_images(prompt="读图", image_paths=[])
        self.assertEqual(post.call_args.args[0], "https://vision.example/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer vision-secret")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen3-vl-plus")
        self.assertEqual(post.call_args.kwargs["json"]["temperature"], 0.2)
        self.assertNotIn("secret", str(client.audit_metadata()))

    def test_partial_route_never_reuses_text_credentials(self) -> None:
        for field in ("VISION_API_KEY", "VISION_BASE_URL", "VISION_MODEL"):
            env = self.env.copy()
            env.pop(field)
            with self.subTest(field=field), patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(ValueError, field):
                    create_llm_client_from_env()
        for url in ("https://user:secret@example.com/v1", "file:///tmp/model", "https://example.com?key=secret"):
            with patch.dict(os.environ, {**self.env, "VISION_BASE_URL": url}, clear=True):
                with self.assertRaises(ValueError):
                    create_llm_client_from_env()

    def test_cache_isolated_by_endpoint_not_key(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            image = Path(root) / "page_1.png"
            image.write_bytes(b"fake-image")
            keys = []
            for endpoint, secret in (("https://one.example/v1", "a"), ("https://two.example/v1", "a"),
                                     ("https://two.example/v1", "b")):
                with patch.dict(os.environ, {**self.env, "VISION_BASE_URL": endpoint, "VISION_API_KEY": secret}, clear=True):
                    client = create_llm_client_from_env()
                extractor = MultimodalFigureSemanticExtractor(vision_client=client)
                keys.append(extractor._cache_key(figure=FigureMetadata(figure_id="Figure 1", caption="图注"), image_paths=[image]))
            self.assertNotEqual(keys[0], keys[1])
            self.assertEqual(keys[1], keys[2])

    def test_report_and_question_use_same_vision_route(self) -> None:
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, self.env, clear=True):
            report = build_default_analysis_service()
            question = build_question_answer_service(Path(root))
            disabled = build_question_answer_service(Path(root), disable_vision=True)
        extractor = report._runtime._research_paper_pipeline._figure_grounding_runner._extractor
        self.assertEqual(extractor._vision_client.vision_model, "qwen3-vl-plus")
        self.assertEqual(question.vision_model, "qwen3-vl-plus")
        self.assertEqual(question.pipeline.vision.delegate._vision_client.vision_model, "qwen3-vl-plus")
        self.assertTrue(question.vision_configuration_fingerprint)
        self.assertIsNone(disabled.vision_model)
        self.assertIsNone(disabled.vision_configuration_fingerprint)
