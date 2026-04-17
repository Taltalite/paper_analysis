import unittest

from paper_analysis.domain.models import FigureMetadata
from paper_analysis.runtime.crews.research.figure_analysis import CrewAIFigureAnalysisRunner


class FigureAnalysisRunnerTest(unittest.TestCase):
    def test_parse_batch_text_allows_newlines_inside_json_strings(self) -> None:
        raw_output = """```json
{
  "analyses": [
    {
      "figure_id": "Figure 1",
      "figure_title_or_caption": "图1概览",
      "experiment_focus": "比较不同方法的整体流程",
      "compared_items": [],
      "metrics_or_axes": ["speed"],
      "main_observations": ["第一行
第二行"],
      "claimed_conclusion": "图中主要展示流程结构。",
      "consistency_check": "正文与图注基本一致。",
      "confidence": "中"
    }
  ]
}
```"""
        batch = CrewAIFigureAnalysisRunner._parse_batch_text(
            raw_text=raw_output,
            figures=[FigureMetadata(figure_id="Figure 1", caption="caption")],
        )

        self.assertEqual(len(batch.analyses), 1)
        self.assertEqual(batch.analyses[0].figure_id, "Figure 1")
        self.assertEqual(batch.analyses[0].confidence, "中")

    def test_fallback_batch_returns_conservative_result(self) -> None:
        batch = CrewAIFigureAnalysisRunner._fallback_batch(
            figures=[FigureMetadata(figure_id="Figure 2", caption="Long caption text")],
            reason="json parse failed",
        )

        self.assertEqual(len(batch.analyses), 1)
        self.assertEqual(batch.analyses[0].figure_id, "Figure 2")
        self.assertEqual(batch.analyses[0].confidence, "不足以判断")
        self.assertIn("自动回退", batch.analyses[0].consistency_check)


if __name__ == "__main__":
    unittest.main()
