"""通过 bash scripts/run.sh python scripts/run_qa_batch.py 运行。"""
import argparse
import asyncio
from pathlib import Path

from paper_analysis.services.qa_evaluation import run_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="问答候选准备检查或真实运行（不作专家评分）")
    parser.add_argument("--manifest", type=Path, default=Path("evals/qa_candidates.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", default="")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--max-followups", type=int, choices=[0, 1, 2], default=0)
    args = parser.parse_args()
    results = asyncio.run(run_candidates(args.manifest, args.output,
        ids=set(args.ids.split(",")) if args.ids else None, max_followups=args.max_followups, real=args.real))
    print(f"记录 {len(results)} 条候选运行；专家效果均未评测。清单：{args.output / 'manifest.json'}")


if __name__ == "__main__":
    main()
