"""真实适配器 smoke：仅合成输入、共享预算、无自动重试。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.execution_context import execution_scope
from paper_analysis.env import load_project_dotenv
from paper_analysis.runtime.budget import BudgetLedger
from scripts.verify_vision import make_visual_fixture


def main() -> None:
    parser = argparse.ArgumentParser(description="合成输入真实模型冒烟，最多两次请求")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ledger_path = args.output / "budget.json"
    if ledger_path.exists():
        raise SystemExit("输出目录已有账本，请使用新目录，避免覆盖历史审计。")
    load_project_dotenv()
    client = create_llm_client_from_env()
    policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(token_budget=8000, max_calls=2,
        max_output_tokens=1024, timeout_seconds=120))
    ledger = BudgetLedger(job_id="synthetic-model-smoke", attempt=1, policy=policy.effective, path=ledger_path)
    results = []
    with execution_scope(ledger):
        try:
            answer = str(client.to_crewai_llm().call("合成测试：3个生物学重复，每个重复测量2次。请用一句中文回答生物学重复数和技术测量总数。"))
            results.append({"case": "kimi_text", "passed": "3" in answer and "6" in answer, "response": answer})
        except Exception as exc:
            results.append({"case": "kimi_text", "passed": False, "error_type": type(exc).__name__})
        try:
            fixture = make_visual_fixture(args.output / "images")
            answer = client.complete_with_images(prompt="请列出两根柱子的英文名称及标注数值，不补充推断。",
                image_paths=[Path(fixture.figures[0].image_block_paths[0])], execution_context=ledger)
            results.append({"case": "qwen_image", "passed": all(x in answer for x in ("Alpha", "Beta", "37", "83")), "response": answer})
        except Exception as exc:
            results.append({"case": "qwen_image", "passed": False, "error_type": type(exc).__name__})
    report = {"scope": "合成输入适配器连通性，不代表论文质量验收", "results": results,
              "execution": ledger.summary(stop_reason="smoke_complete").model_dump(mode="json")}
    (args.output / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"results": [{k: v for k, v in r.items() if k != "response"} for r in results],
                      "tokens": report["execution"]["actual_usage"], "calls": report["execution"]["call_count"]}, ensure_ascii=False))
    if not all(result["passed"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
