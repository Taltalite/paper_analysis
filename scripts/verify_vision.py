"""显式运行真实视觉接口；默认只发送自动生成的非敏感测试图。

用法：KIMI_VISION_MODEL=... bash scripts/run.sh python scripts/verify_vision.py
可用 --pdf 指定论文，--limit 控制图表数量。结果为 noop 时退出码非零。
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import fitz

from paper_analysis.adapters.llm.base import VisionLLMClient
from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.env import load_project_dotenv


def make_visual_fixture(directory: Path) -> ParsedDocument:
    """数值只出现在图片内，用于区分真正读图与复述提示词。"""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "vision_probe.png"
    with fitz.open() as pdf:
        page = pdf.new_page(width=640, height=480)
        page.insert_text((40, 45), "Figure 1: Synthetic visual input test", fontsize=18)
        page.draw_line((90, 370), (570, 370))
        page.draw_line((90, 370), (90, 85))
        page.insert_text((18, 75), "Score", fontsize=14)
        for x, height, value, label, color in (
            (170, 74, "37", "Alpha", (0.2, 0.4, 0.9)),
            (360, 166, "83", "Beta", (0.9, 0.4, 0.2)),
        ):
            page.draw_rect(fitz.Rect(x, 370-height, x+90, 370), color=color, fill=color)
            page.insert_text((x+30, 360-height), value, fontsize=20)
            page.insert_text((x+15, 400), label, fontsize=16)
        page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(path)
    return ParsedDocument(title="合成视觉输入测试", figures=[FigureMetadata(
        figure_id="Figure 1", caption="Figure 1: Synthetic visual input test",
        image_block_paths=[str(path)],
    )])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--figure-id", help='只验证指定图号，例如 "Figure 4"')
    parser.add_argument("--output", type=Path, default=Path("output/vision-verification"))
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit 必须大于零")
    load_project_dotenv()
    client = create_llm_client_from_env()
    if not isinstance(client, VisionLLMClient) or not client.vision_model:
        print("未配置视觉模型：请设置 KIMI_VISION_MODEL 或 OPENAI_VISION_MODEL。")
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    document = asyncio.run(PdfParser().parse(args.pdf)) if args.pdf else make_visual_fixture(args.output / "images")
    figures = [figure for figure in document.figures if not args.figure_id or figure.figure_id == args.figure_id]
    batch = MultimodalFigureSemanticExtractor(vision_client=client).extract(document=document, figures=figures[:args.limit])
    output = args.output / "semantic.json"
    output.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    success = bool(batch.artifacts) and all(a.extraction_source == "multimodal_llm" for a in batch.artifacts)
    if not args.pdf:
        # 这些标记未放入图注或提示词，只能来自图片。
        observed = json.dumps([a.model_dump() for a in batch.artifacts], ensure_ascii=False)
        success = success and all(token in observed for token in ("Alpha", "Beta", "37", "83"))
    print(json.dumps({"通过": success, "图表数": len(batch.artifacts), "结果路径": str(output),
                      "来源": [a.extraction_source for a in batch.artifacts]}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
