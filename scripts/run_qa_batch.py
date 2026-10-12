"""通过 bash scripts/run.sh python scripts/run_qa_batch.py 运行。"""
import argparse
import asyncio
from pathlib import Path

from paper_analysis.services.qa_evaluation import DEFAULT_BATCH_TOKEN_BUDGET, run_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="问答候选准备检查或真实运行（不作专家评分）")
    parser.add_argument("--manifest", type=Path, default=Path("evals/qa_candidates.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", default="")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--max-followups", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--token-budget", type=int, default=DEFAULT_BATCH_TOKEN_BUDGET, help="整个顺序批次共享额度（默认与 standard 一致）")
    parser.add_argument("--max-calls", type=int, default=32)
    parser.add_argument("--max-output-tokens", type=int, help="单请求输出上限；不修改服务默认档位")
    parser.add_argument("--timeout-seconds", type=float, help="每题执行时限")
    args = parser.parse_args()
    results = asyncio.run(run_candidates(args.manifest, args.output,
        ids=set(args.ids.split(",")) if args.ids else None, max_followups=args.max_followups, real=args.real,
        token_budget=args.token_budget, max_calls=args.max_calls,
        max_output_tokens=args.max_output_tokens, timeout_seconds=args.timeout_seconds))
    print(f"记录 {len(results)} 条候选运行；专家效果均未评测。清单：{args.output / 'manifest.json'}")
    if args.real and (not results or any(
        result.execution in {"not_called", "configuration_failed", "execution_failed"}
        or any(value is False for value in result.engineering_checks.values()) for result in results
    )):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
