from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.api.app import create_app
from paper_analysis.api.deps import get_job_executor, get_job_service
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.job_service import JobService


class FakeAnalysisService:
    async def parse_file(self, path: Path) -> ParsedDocument:
        raw_text = path.read_text(encoding="utf-8", errors="ignore") or "dummy pdf body"
        if path.suffix.lower() == ".pdf":
            return ParsedDocument(
                title="Test Paper",
                raw_text=raw_text,
                markdown="# Parsed PDF Structure\n\n## Abstract\nSynthetic abstract",
                sections={"abstract": "Synthetic abstract", "results": "Synthetic results"},
                section_order=["abstract", "results"],
                figures=[
                    FigureMetadata(
                        figure_id="Figure 1",
                        caption="Synthetic figure caption",
                        page_number=1,
                        referenced_text_spans=["Synthetic figure reference"],
                    )
                ],
                metadata={"parser_kind": "pdf", "page_count": 1, "authors": ["Tester"]},
            )
        return ParsedDocument(
            title="Plain Text Test",
            raw_text=raw_text,
            markdown="",
            sections={"body": raw_text},
            section_order=["body"],
            metadata={"parser_kind": "plain_text"},
        )

    async def analyze_document(self, document: ParsedDocument, mode: AnalysisMode) -> AnalysisResult:
        return AnalysisResult(
            title=document.title,
            summary=f"Summary for {mode.value}",
            key_points=["Synthetic key point"],
            limitations=["Synthetic limitation"],
            markdown_report="# Report\n\nSynthetic report body",
            structured_data={
                "metadata": {"title": document.title},
                "figure_analyses": [{"figure_id": "Figure 1", "claimed_conclusion": "Synthetic claim"}],
            },
        )


class ImmediateJobExecutor:
    async def submit_job(self, *, job_service: JobService, job_id) -> None:  # noqa: ANN001
        await job_service.run_job(job_id)


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        base_dir = Path(self._temp_dir.name)
        job_service = JobService(
            job_store=LocalFilesystemJobStore(base_dir=base_dir / "store"),
            artifact_service=ArtifactService(storage=LocalFilesystemArtifactStorage()),
            analysis_service=FakeAnalysisService(),
            workspace_root=base_dir / "workspace",
        )

        app = create_app()
        app.dependency_overrides[get_job_service] = lambda: job_service
        app.dependency_overrides[get_job_executor] = lambda: ImmediateJobExecutor()
        self.client = TestClient(app)
        self.job_service = job_service

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_pdf_job_happy_path(self) -> None:
        response = self.client.post(
            "/api/analysis/jobs",
            data={"mode": "research_paper"},
            files={"file": ("sample.pdf", b"%PDF-1.4 synthetic", "application/pdf")},
        )
        self.assertEqual(response.status_code, 202)
        created_job = response.json()
        self.assertEqual(created_job["status"], "pending")

        job_id = created_job["id"]
        job_response = self.client.get(f"/api/analysis/jobs/{job_id}")
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.json()["status"], "completed")

        progress_response = self.client.get(f"/api/analysis/jobs/{job_id}/progress")
        self.assertEqual(progress_response.status_code, 200)
        progress_payload = progress_response.json()
        self.assertEqual(progress_payload["job"]["status"], "completed")
        self.assertEqual(progress_payload["current_stage"], "任务完成")
        self.assertEqual(progress_payload["progress_percent"], 100)
        self.assertTrue(progress_payload["recent_logs"])
        self.assertIn("任务开始执行", "\n".join(progress_payload["recent_logs"]))
        self.assertEqual(len(progress_payload["steps"]), 4)

        report_response = self.client.get(f"/api/analysis/jobs/{job_id}/report")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()
        self.assertIn("# Report", report_payload["markdown_report"])
        self.assertIn("# Parsed PDF Structure", report_payload["parsed_markdown"])

        artifact_response = self.client.get(f"/api/analysis/jobs/{job_id}/artifact")
        self.assertEqual(artifact_response.status_code, 200)
        artifact_payload = artifact_response.json()
        self.assertEqual(artifact_payload["status"], "completed")
        self.assertIn("structured_data", artifact_payload["json_report"])
        self.assertIn("figure_analyses", artifact_payload["json_report"]["structured_data"])
        self.assertIn("# Report", artifact_payload["markdown_report"])
        log_path = Path(artifact_payload["artifact"]["log_path"])
        self.assertTrue(log_path.exists())
        self.assertIn("任务开始执行", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
