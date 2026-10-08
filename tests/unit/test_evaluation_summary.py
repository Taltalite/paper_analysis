import unittest

from paper_analysis.services.qa_evaluation import CandidateRun, summarize_checks


class EvaluationSummaryTests(unittest.TestCase):
    def test_na_and_missing_are_not_success(self) -> None:
        records = [CandidateRun(candidate_id=str(i), execution="test", engineering_checks=value)
                   for i, value in enumerate([{"vision": True}, {"vision": False},
                                             {"vision": "not_applicable"}, {}])]
        self.assertEqual(summarize_checks(records)["vision"], {
            "passed": 1, "failed": 1, "not_applicable": 1, "not_evaluated": 1, "pass_rate": 0.5})
        self.assertEqual(summarize_checks([]), {})
