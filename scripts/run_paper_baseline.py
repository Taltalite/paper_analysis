"""通过 bash scripts/run.sh python scripts/run_paper_baseline.py 使用。"""
import argparse
import asyncio
from pathlib import Path

from paper_analysis.services.paper_baseline import run_paper_batches


def main() -> None:
    parser = argparse.ArgumentParser(description="每篇论文独立使用 standard 默认额度的固定问答基线")
    parser.add_argument("--manifest", type=Path, default=Path("evals/datasets/paper_qa_v1/candidates.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--max-followups", type=int, choices=[0, 1, 2], default=0)
    args = parser.parse_args()
    report = asyncio.run(run_paper_batches(args.manifest, args.output, real=args.real, max_followups=args.max_followups))
    print(f"已记录 {len(report.results)} 道固定问题：{args.output / 'baseline_manifest.json'}；默认额度见 run_settings。")
    if args.real and any(r.execution in {"not_called", "configuration_failed", "execution_failed"}
                        or any(v is False for v in r.engineering_checks.values()) for r in report.results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
