from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from paper_analysis.adapters.storage.base import JobStore
from paper_analysis.domain.enums import AnalysisMode, DocumentKind, JobStatus
from paper_analysis.domain.schemas import (
    AnalysisArtifact,
    AnalysisJob,
    ArtifactContentResponse,
    MarkdownReportResponse,
)
from paper_analysis.services.analysis_service import AnalysisService
from paper_analysis.services.artifact_service import ArtifactService


class JobService:
    def __init__(
        self,
        *,
        job_store: JobStore,
        artifact_service: ArtifactService,
        analysis_service: AnalysisService,
        workspace_root: Path,
    ) -> None:
        self._job_store = job_store
        self._artifact_service = artifact_service
        self._analysis_service = analysis_service
        self._workspace_root = workspace_root

    async def create_job_from_upload(
        self,
        *,
        filename: str,
        content: bytes,
        mode: AnalysisMode,
        document_kind: DocumentKind,
    ) -> AnalysisJob:
        job = AnalysisJob(mode=mode, document_kind=document_kind, filename=filename)
        input_path = self._job_workspace(job.id) / f"source{self._suffix_for(filename, document_kind)}"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_bytes(content)
        job.input_path = str(input_path)
        return await self._job_store.save(job)

    async def get_job(self, job_id: UUID) -> AnalysisJob:
        return await self._job_store.get(job_id)

    async def run_job(self, job_id: UUID) -> AnalysisJob:
        job = await self._job_store.get(job_id)
        if not job.input_path:
            return await self._fail_job(job, "输入文件缺失。")

        input_path = Path(job.input_path)
        try:
            await self._update_job(job, status=JobStatus.PARSING)
            parsed_document = await self._analysis_service.parse_file(input_path)

            await self._update_job(job, status=JobStatus.ANALYZING)
            result = await self._analysis_service.analyze_document(parsed_document, job.mode)

            markdown_path = self._job_workspace(job.id) / "report.md"
            json_path = self._job_workspace(job.id) / "report.json"
            artifact = await self._artifact_service.save_analysis_result(
                markdown_path=markdown_path,
                json_path=json_path,
                result=result,
                document=parsed_document,
            )
            job.artifact = artifact
            return await self._update_job(job, status=JobStatus.COMPLETED, error_message=None)
        except Exception as exc:
            return await self._fail_job(job, str(exc))

    async def get_markdown_report(self, job_id: UUID) -> MarkdownReportResponse:
        job = await self._job_store.get(job_id)
        self._ensure_completed(job)

        markdown_path = self._required_path(job.artifact.markdown_report_path, "Markdown report")
        markdown_report = await self._artifact_service.read_markdown_report(markdown_path)

        parsed_markdown = None
        if job.artifact.parsed_markdown_path:
            parsed_markdown = await self._artifact_service.read_markdown_report(
                Path(job.artifact.parsed_markdown_path)
            )

        return MarkdownReportResponse(
            job_id=job.id,
            status=job.status,
            markdown_report=markdown_report,
            parsed_markdown=parsed_markdown,
        )

    async def get_artifact_content(self, job_id: UUID) -> ArtifactContentResponse:
        job = await self._job_store.get(job_id)
        self._ensure_completed(job)

        markdown_report = await self._artifact_service.read_markdown_report(
            self._required_path(job.artifact.markdown_report_path, "Markdown report")
        )
        json_report = await self._artifact_service.read_json_report(
            self._required_path(job.artifact.json_report_path, "JSON report")
        )

        parsed_markdown = None
        if job.artifact.parsed_markdown_path:
            parsed_markdown = await self._artifact_service.read_markdown_report(
                Path(job.artifact.parsed_markdown_path)
            )

        return ArtifactContentResponse(
            job_id=job.id,
            status=job.status,
            artifact=job.artifact,
            markdown_report=markdown_report,
            parsed_markdown=parsed_markdown,
            json_report=json_report,
        )

    async def _update_job(
        self,
        job: AnalysisJob,
        *,
        status: JobStatus,
        error_message: str | None = None,
    ) -> AnalysisJob:
        job.status = status
        job.error_message = error_message
        job.updated_at = datetime.now(UTC)
        return await self._job_store.save(job)

    async def _fail_job(self, job: AnalysisJob, error_message: str) -> AnalysisJob:
        job.artifact = job.artifact or AnalysisArtifact()
        return await self._update_job(job, status=JobStatus.FAILED, error_message=error_message)

    def _job_workspace(self, job_id: UUID) -> Path:
        return self._workspace_root / str(job_id)

    @staticmethod
    def _suffix_for(filename: str, document_kind: DocumentKind) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix:
            return suffix
        if document_kind == DocumentKind.PDF:
            return ".pdf"
        return ".txt"

    @staticmethod
    def _ensure_completed(job: AnalysisJob) -> None:
        if job.status != JobStatus.COMPLETED:
            raise FileNotFoundError(f"任务 {job.id} 的产物尚未准备完成。")

    @staticmethod
    def _required_path(path: str | None, label: str) -> Path:
        if not path:
            raise FileNotFoundError(f"{label}尚不可用。")
        return Path(path)
