from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Literal
from uuid import UUID

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.adapters.parser.qa_cache import ParsedDocumentCache, render_page
from paper_analysis.adapters.storage.qa_store import QuestionStore, atomic_json
from paper_analysis.domain.qa import AnswerResponse, QuestionAudit, QuestionJob, QuestionRequest, QuestionRound
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline


class QuestionAnswerService:
    def __init__(self, *, parser: DocumentParser, pipeline: QuestionAnswerPipeline, root: Path,
                 execution_kind: Literal["real_call", "offline_test"] = "offline_test",
                 model: str = "fake", vision_model: str | None = None) -> None:
        self.parser, self.pipeline, self.root = parser, pipeline, root.resolve()
        self.store = QuestionStore(self.root)
        self.cache = ParsedDocumentCache(self.root / "cache", parser)
        self.execution_kind, self.model, self.vision_model = execution_kind, model, vision_model

    def prepare(self, *, filename: str, content: bytes, request: QuestionRequest) -> QuestionJob:
        if not filename.lower().endswith(".pdf") or not content.startswith(b"%PDF-"):
            raise ValueError("请上传有效的单篇 PDF。")
        if len(content) > 30 * 1024 * 1024:
            raise ValueError("PDF 不能超过 30 MB。")
        job = QuestionJob(filename=Path(filename).name, request=request, document_sha256=hashlib.sha256(content).hexdigest())
        directory = self.store.directory(job.id)
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(content)
        atomic_json(directory / "request.json", request)
        self.store.save(job)
        return job

    async def ask(self, *, filename: str, content: bytes, request: QuestionRequest) -> AnswerResponse:
        job = self.prepare(filename=filename, content=content, request=request)
        job.status, job.stage = "running", "解析与核验"
        self.store.save(job)
        try:
            response = await asyncio.to_thread(self.execute, job.id, job.attempt)
        except Exception as exc:
            job.status, job.stage, job.error = "failed", "执行失败", "PDF 解析或问答执行失败。"
            self.store.save(job)
            raise ValueError(job.error) from exc
        self.complete(job, response)
        return response

    def execute(self, identifier: UUID, attempt: int) -> AnswerResponse:
        job = self.store.get(identifier)
        if job.attempt != attempt or job.status != "running":
            raise ValueError("任务轮次已过期。")
        started = time.monotonic()
        directory = self.store.directory(identifier)
        source = directory / "source.pdf"
        if hashlib.sha256(source.read_bytes()).hexdigest() != job.document_sha256:
            raise ValueError("PDF 指纹与任务记录不符。")
        audit = QuestionAudit(job_id=identifier, attempt=attempt, document_sha256=job.document_sha256,
            execution_kind=self.execution_kind, model=self.model, vision_model=self.vision_model,
            parser_version=self.cache.version)
        package = Path(__file__).parents[1]
        runtime_files = [package / "config/qa_prompt.txt", package / "runtime/pipelines/question_answer.py",
                         package / "runtime/pipelines/qa_quality.py", package / "runtime/crews/research/fact_check.py",
                         package / "runtime/crews/research/question_answer.py"]
        audit.runtime_fingerprint = hashlib.sha256(b"".join(path.read_bytes() for path in runtime_files)).hexdigest()
        audit_path = directory / f"audit-{attempt}.json"
        atomic_json(audit_path, audit)
        def record(item: QuestionRound) -> None:
            audit.rounds.append(item)
            audit.total_seconds = round(time.monotonic() - started, 3)
            atomic_json(audit_path, audit)
        try:
            document, hit = self.cache.get(source)
            audit.parse_cache_hit = hit
            audit.parse_seconds = round(time.monotonic() - started, 3)
            atomic_json(directory / "parsed.json", document)
            atomic_json(audit_path, audit)
            if isinstance(self.pipeline, QuestionAnswerPipeline):
                response = self.pipeline.run(document=document, request=job.request, audit_sink=record)
            else:
                response = self.pipeline.run(document=document, request=job.request)
            response.id, response.document_sha256 = identifier, job.document_sha256
            audit.stop_reason = response.stop_reason
            atomic_json(directory / f"result-{attempt}.json", response)
            return response
        except Exception:
            audit.stop_reason = "execution_failed"
            raise
        finally:
            audit.total_seconds = round(time.monotonic() - started, 3)
            atomic_json(audit_path, audit)

    def complete(self, job: QuestionJob, response: AnswerResponse) -> None:
        current = self.store.get(job.id)
        if current.attempt != job.attempt or current.status != "running":
            return
        if response.id != job.id or response.document_sha256 != current.document_sha256:
            raise ValueError("回答与当前任务的文档绑定不一致，禁止发布。")
        atomic_json(self.store.directory(job.id) / "answer.json", response)
        current.status, current.stage = "completed", "回答已完成"
        self.store.save(current)

    def get(self, identifier: UUID) -> AnswerResponse:
        directory = self.store.directory(identifier)
        if (directory / "job.json").exists() and self.store.get(identifier).status != "completed":
            raise FileNotFoundError("问答尚未完成。")
        return AnswerResponse.model_validate_json((directory / "answer.json").read_text(encoding="utf-8"))

    def audit(self, identifier: UUID) -> QuestionAudit:
        job = self.store.get(identifier)
        result = QuestionAudit.model_validate_json((self.store.directory(identifier) / f"audit-{job.attempt}.json").read_text())
        if job.status in {"failed", "timed_out", "cancelled"}:
            result.stop_reason = job.status
        return result

    def page(self, identifier: UUID, page: int, evidence_id: str | None = None) -> Path:
        job = self.store.get(identifier)
        source = self.store.directory(identifier) / "source.pdf"
        if hashlib.sha256(source.read_bytes()).hexdigest() != job.document_sha256:
            raise ValueError("PDF 指纹不一致。")
        box = None
        if evidence_id:
            answer = self.get(identifier)
            evidence = next((e for e in answer.evidence if e.evidence_id == evidence_id), None)
            if evidence is None or page not in {evidence.page, *evidence.image_pages}:
                raise ValueError("证据与请求页面不匹配。")
            box = evidence.bbox if page == evidence.page else None
        return render_page(source, page, highlight=box)


def build_question_answer_service(root: Path = Path(".data/questions"), *, disable_vision: bool = False) -> QuestionAnswerService:
    from paper_analysis.adapters.llm.base import VisionLLMClient
    from paper_analysis.adapters.llm.factory import create_llm_client_from_env
    from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
    from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
    from paper_analysis.adapters.parser.pdf import PdfParser
    from paper_analysis.runtime.crews.research.fact_check import CrewAIFactCheckRunner
    from paper_analysis.runtime.crews.research.question_answer import CrewAIQuestionAnswerRunner

    from paper_analysis.adapters.parser.qa_cache import OnDemandFigureExtractor
    client = create_llm_client_from_env()
    metadata = client.audit_metadata()
    vision = MultimodalFigureSemanticExtractor(vision_client=client) if not disable_vision and isinstance(client, VisionLLMClient) and client.vision_model else NoopFigureSemanticExtractor()
    return QuestionAnswerService(parser=PdfParser(render_assets=False), root=root,
        execution_kind="real_call", model=metadata["model"] or "unknown",
        vision_model=None if disable_vision else metadata["vision_model"],
        pipeline=QuestionAnswerPipeline(runner=CrewAIQuestionAnswerRunner(client),
            checker=CrewAIFactCheckRunner(llm_client=client, verbose=False), vision=OnDemandFigureExtractor(vision)))
