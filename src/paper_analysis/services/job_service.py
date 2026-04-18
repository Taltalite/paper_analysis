from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from paper_analysis.adapters.storage.base import JobStore
from paper_analysis.domain.enums import AnalysisMode, DocumentKind, JobStatus
from paper_analysis.domain.schemas import (
    AnalysisArtifact,
    AnalysisJob,
    ArtifactContentResponse,
    JobProgressResponse,
    JobProgressStep,
    MarkdownReportResponse,
)
from paper_analysis.services.analysis_service import AnalysisService
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.job_logging import capture_job_logs


logger = logging.getLogger(__name__)


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
        job.artifact.log_path = str(self._job_log_path(job.id, job.created_at))
        return await self._job_store.save(job)

    async def get_job(self, job_id: UUID) -> AnalysisJob:
        return await self._job_store.get(job_id)

    async def get_job_progress(self, job_id: UUID) -> JobProgressResponse:
        job = await self._job_store.get(job_id)
        recent_logs = self._read_recent_logs(job.artifact.log_path)
        current_stage, progress_percent, summary_message = self._build_progress_snapshot(job, recent_logs)
        return JobProgressResponse(
            job=job,
            current_stage=current_stage,
            progress_percent=progress_percent,
            summary_message=summary_message,
            recent_logs=recent_logs,
            steps=self._build_progress_steps(job),
        )

    async def run_job(self, job_id: UUID) -> AnalysisJob:
        job = await self._job_store.get(job_id)
        if not job.input_path:
            return await self._fail_job(job, "输入文件缺失。")

        input_path = Path(job.input_path)
        if not job.artifact.log_path:
            job.artifact.log_path = str(self._job_log_path(job.id, datetime.now(UTC)))
            job = await self._job_store.save(job)
        log_path = Path(job.artifact.log_path)
        try:
            with capture_job_logs(log_path):
                try:
                    logger.info("任务开始执行。job_id=%s filename=%s", job.id, job.filename)
                    await self._update_job(job, status=JobStatus.PARSING)
                    logger.info("开始解析输入文件：%s", input_path)
                    parsed_document = await self._analysis_service.parse_file(input_path)
                    logger.info(
                        "解析完成。parser_kind=%s section_count=%s figure_count=%s",
                        parsed_document.metadata.get("parser_kind"),
                        len(parsed_document.sections),
                        len(parsed_document.figures),
                    )

                    await self._update_job(job, status=JobStatus.ANALYZING)
                    logger.info("开始执行分析。mode=%s", job.mode.value)
                    result = await self._analysis_service.analyze_document(parsed_document, job.mode)
                    logger.info(
                        "分析完成。summary_length=%s structured_keys=%s",
                        len(result.summary),
                        sorted(result.structured_data.keys()),
                    )

                    markdown_path = self._job_workspace(job.id) / "report.md"
                    json_path = self._job_workspace(job.id) / "report.json"
                    artifact = await self._artifact_service.save_analysis_result(
                        markdown_path=markdown_path,
                        json_path=json_path,
                        result=result,
                        document=parsed_document,
                    )
                    artifact.log_path = str(log_path)
                    job.artifact = artifact
                    logger.info(
                        "产物保存完成。markdown=%s json=%s parsed=%s log=%s",
                        artifact.markdown_report_path,
                        artifact.json_report_path,
                        artifact.parsed_markdown_path,
                        artifact.log_path,
                    )
                    return await self._update_job(job, status=JobStatus.COMPLETED, error_message=None)
                except Exception:
                    logger.exception("任务执行失败。job_id=%s", job.id)
                    raise
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
        previous_status = job.status
        job.status = status
        job.error_message = error_message
        job.updated_at = datetime.now(UTC)
        logger.info(
            "任务状态更新。job_id=%s from=%s to=%s error=%s",
            job.id,
            previous_status.value if hasattr(previous_status, "value") else previous_status,
            status.value,
            error_message or "",
        )
        return await self._job_store.save(job)

    async def _fail_job(self, job: AnalysisJob, error_message: str) -> AnalysisJob:
        job.artifact = job.artifact or AnalysisArtifact()
        return await self._update_job(job, status=JobStatus.FAILED, error_message=error_message)

    def _job_workspace(self, job_id: UUID) -> Path:
        return self._workspace_root / str(job_id)

    def _job_log_path(self, job_id: UUID, timestamp: datetime) -> Path:
        stamp = timestamp.astimezone().strftime("%Y%m%d_%H%M%S")
        return self._job_workspace(job_id) / "logs" / f"analysis_{stamp}.log"

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

    @staticmethod
    def _read_recent_logs(log_path: str | None, max_lines: int = 30) -> list[str]:
        if not log_path:
            return []
        path = Path(log_path)
        if not path.exists():
            return []

        lines = [line.rstrip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
        meaningful = [line for line in lines if line.strip()]
        return meaningful[-max_lines:]

    @staticmethod
    def _build_progress_snapshot(job: AnalysisJob, recent_logs: list[str]) -> tuple[str, int, str]:
        stage_mapping = {
            JobStatus.PENDING: ("任务排队", 10, "后端已接收文件，等待进入执行队列。"),
            JobStatus.PARSING: ("文档解析", 35, "正在解析文档结构并提取可分析内容。"),
            JobStatus.ANALYZING: ("多 Agent 分析", 70, "正在执行多 agent 分析与报告生成。"),
            JobStatus.COMPLETED: ("任务完成", 100, "分析完成，报告和结构化结果已生成。"),
            JobStatus.FAILED: ("任务失败", 100, "任务执行失败，请结合日志定位原因。"),
        }
        current_stage, progress_percent, fallback_message = stage_mapping.get(
            job.status,
            ("状态未知", 0, "任务状态未知。"),
        )

        if recent_logs:
            return current_stage, progress_percent, recent_logs[-1]
        if job.error_message:
            return current_stage, progress_percent, job.error_message
        return current_stage, progress_percent, fallback_message

    @staticmethod
    def _build_progress_steps(job: AnalysisJob) -> list[JobProgressStep]:
        if job.status == JobStatus.FAILED:
            upload_status = "completed"
            parsing_status = "completed" if job.updated_at and job.artifact.log_path else "pending"
            analysis_status = "failed" if job.status == JobStatus.FAILED else "pending"
            output_status = "failed"
            return [
                JobProgressStep(key="upload", label="文件接收", status=upload_status),
                JobProgressStep(key="parse", label="文档解析", status=parsing_status),
                JobProgressStep(key="analyze", label="多 Agent 分析", status=analysis_status),
                JobProgressStep(key="artifact", label="结果生成", status=output_status),
            ]

        mapping = {
            JobStatus.PENDING: ["active", "pending", "pending", "pending"],
            JobStatus.PARSING: ["completed", "active", "pending", "pending"],
            JobStatus.ANALYZING: ["completed", "completed", "active", "pending"],
            JobStatus.COMPLETED: ["completed", "completed", "completed", "completed"],
        }
        statuses = mapping.get(job.status, ["pending", "pending", "pending", "pending"])
        labels = [
            ("upload", "文件接收"),
            ("parse", "文档解析"),
            ("analyze", "多 Agent 分析"),
            ("artifact", "结果生成"),
        ]
        return [
            JobProgressStep(key=key, label=label, status=status)
            for (key, label), status in zip(labels, statuses, strict=True)
        ]
