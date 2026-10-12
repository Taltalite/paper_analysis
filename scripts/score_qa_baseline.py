"""通过 bash scripts/run.sh python scripts/score_qa_baseline.py 使用。"""
import argparse
from pathlib import Path

from paper_analysis.services.reference_evaluation import (
    create_review_template, load_reference, prepare_candidates, save_score, score_run, validate_sources,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="固定论文参考集校验、候选生成、独立评价模板和评分")
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/paper_qa_v1/reference.json"))
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--prepare-candidates", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--write-review-template", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = load_reference(args.dataset)
    if args.validate:
        print(validate_sources(dataset))
    if args.prepare_candidates:
        prepare_candidates(dataset, args.prepare_candidates)
        print(f"已生成 {len(dataset.cases)} 条问题；参考答案未进入候选清单。")
    if args.write_review_template:
        if not args.run:
            parser.error("评价模板需要 --run。")
        create_review_template(args.dataset, args.run, args.write_review_template)
    if args.output:
        if not args.run:
            parser.error("评分需要 --run。")
        report = score_run(args.dataset, args.run, review_path=args.review)
        save_score(report, args.output)
        print(f"已保存评分：{args.output / 'scores.md'}")
    if not any((args.validate, args.prepare_candidates, args.write_review_template, args.output)):
        parser.error("请选择校验、候选生成、评价模板或评分操作。")


if __name__ == "__main__":
    main()
