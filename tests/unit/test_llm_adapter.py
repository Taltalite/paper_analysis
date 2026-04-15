import unittest

from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM


class OpenAICompatibleLLMTest(unittest.TestCase):
    def test_builds_crewai_llm(self) -> None:
        adapter = OpenAICompatibleLLM(
            model="gpt-4o-mini",
            api_key="test-key",
            base_url="https://example.com/v1",
            provider="openai",
        )

        llm = adapter.to_crewai_llm()

        self.assertEqual(llm.model, "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()
