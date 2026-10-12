"""真实适配器 smoke：仅合成输入、共享预算、无自动重试。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import httpx

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.execution_context import execution_scope
from paper_analysis.env import load_project_dotenv
from paper_analysis.runtime.budget import BudgetLedger
from scripts.verify_vision import make_visual_fixture


def main() -> None:
    parser = argparse.ArgumentParser(description="合成输入真实模型冒烟，最多两次请求")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--configured-limits", action="store_true",
                        help="按当前 standard 输出上限和视觉配置验证；保留最多两次请求")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ledger_path = args.output / "budget.json"
    if ledger_path.exists():
        raise SystemExit("输出目录已有账本，请使用新目录，避免覆盖历史审计。")
    load_project_dotenv()
    client = create_llm_client_from_env()
    if client is None:
        raise SystemExit("未配置可用模型，请检查项目 .env。")
    requested = ExecutionPolicyRequest(max_calls=2) if args.configured_limits else ExecutionPolicyRequest(
        token_budget=8000, max_calls=2, max_output_tokens=1024, timeout_seconds=120)
    policy = ResolvedPolicy.resolve(requested)
    ledger = BudgetLedger(job_id="synthetic-model-smoke", attempt=1, policy=policy.effective, path=ledger_path)
    results = []
    http_requests: list[dict] = []
    original_send = httpx.HTTPTransport.handle_request
    current_case = "kimi_text"

    def tracked_send(transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        # 在预算 request hook 之后记录真正发出的公开参数，绝不记录请求头、密钥或正文。
        body = json.loads(request.content)
        record = {"case": current_case, "endpoint": str(request.url), "request_parameters": {
            key: body[key] for key in ("model", "reasoning_effort", "temperature", "max_tokens", "stream")
            if key in body}}
        http_requests.append(record)
        started = perf_counter()
        try:
            response = original_send(transport, request)
            response.read()
            record["status_code"] = response.status_code
            if response.is_success:
                data = response.json()
                record["response_model"] = data.get("model")
                record["finish_reasons"] = [choice.get("finish_reason") for choice in data.get("choices", [])]
                record["usage"] = data.get("usage")
            return response
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            raise
        finally:
            record["elapsed_seconds"] = round(perf_counter() - started, 3)

    with execution_scope(ledger), patch.object(httpx.HTTPTransport, "handle_request", tracked_send):
        try:
            answer = str(client.to_crewai_llm().call("合成测试：3个生物学重复，每个重复测量2次。请用一句中文回答生物学重复数和技术测量总数。"))
            results.append({"case": "kimi_text", "passed": "3" in answer and "6" in answer, "response": answer})
        except Exception as exc:
            results.append({"case": "kimi_text", "passed": False, "error_type": type(exc).__name__})
        current_case = "qwen_image"
        try:
            fixture = make_visual_fixture(args.output / "images")
            answer = client.complete_with_images(prompt="请列出两根柱子的英文名称及标注数值，不补充推断。",
                image_paths=[Path(fixture.figures[0].image_block_paths[0])], execution_context=ledger)
            results.append({"case": "qwen_image", "passed": all(x in answer for x in ("Alpha", "Beta", "37", "83")), "response": answer})
        except Exception as exc:
            results.append({"case": "qwen_image", "passed": False, "error_type": type(exc).__name__})
    metadata = client.audit_metadata()
    expected = [
        {"model": metadata["model"], "temperature": client._temperature,
         "max_tokens": policy.effective.max_output_tokens},
        {"model": metadata["vision_model"], "temperature": client._vision_temperature,
         "max_tokens": min(client._vision_max_output_tokens, policy.effective.max_output_tokens)},
    ]
    if metadata["reasoning_effort"] is not None:
        expected[0]["reasoning_effort"] = metadata["reasoning_effort"]
    for result, wanted in zip(results, expected):
        matching = [item for item in http_requests if item["case"] == result["case"]]
        result["parameters_passed"] = len(matching) == 1 and all(
            matching[0]["request_parameters"].get(key) == value for key, value in wanted.items()) and (
                matching[0]["request_parameters"].get("reasoning_effort") == wanted.get("reasoning_effort"))
        result["passed"] = result["passed"] and result["parameters_passed"]
    report = {"scope": "合成输入适配器连通性，不代表论文质量验收", "results": results,
              "configured_limits": args.configured_limits, "configuration": metadata,
              "http_requests": http_requests,
              "execution": ledger.summary(stop_reason="smoke_complete").model_dump(mode="json")}
    (args.output / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"results": [{k: v for k, v in r.items() if k != "response"} for r in results],
                      "tokens": report["execution"]["actual_usage"], "calls": report["execution"]["call_count"]}, ensure_ascii=False))
    if not all(result["passed"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
