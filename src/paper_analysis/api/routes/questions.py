from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request, Query
from fastapi.responses import FileResponse
from pydantic import ValidationError

from paper_analysis.domain.qa import AnswerResponse, QuestionRequest, QuestionJob, QuestionAudit
from paper_analysis.services.question_jobs import QuestionJobs
from paper_analysis.services.question_answer_service import QuestionAnswerService, build_question_answer_service

router = APIRouter(prefix="/api/qa", tags=["questions"])


@lru_cache
def get_question_service() -> QuestionAnswerService:
    return build_question_answer_service()


def get_jobs(request: Request) -> QuestionJobs:
    return request.app.state.qa_jobs


def parse_request(question: str = Form(...), figure: str | None = Form(None), panel: str | None = Form(None),
                  max_followups: int = Form(2)) -> QuestionRequest:
    try:
        return QuestionRequest(question=question, figure=figure or None, panel=panel or None, max_followups=max_followups)
    except ValidationError as exc:
        raise HTTPException(422, "问题不能为空，图号/子图格式须正确，补取次数须为 0–2。") from exc


@router.post("/jobs", response_model=QuestionJob, status_code=202)
async def submit_question(file: UploadFile = File(...), request: QuestionRequest = Depends(parse_request),
                          jobs: QuestionJobs = Depends(get_jobs)) -> QuestionJob:
    content = await file.read(30 * 1024 * 1024 + 1)
    try:
        return jobs.submit(filename=file.filename or "", content=content, request=request)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs", response_model=list[QuestionJob])
def list_jobs(jobs: QuestionJobs = Depends(get_jobs)) -> list[QuestionJob]:
    return jobs.service.store.list()[:100]


@router.get("/jobs/{identifier}", response_model=QuestionJob)
def job_status(identifier: UUID, jobs: QuestionJobs = Depends(get_jobs)) -> QuestionJob:
    try:
        job = jobs.service.store.get(identifier)
        if job.status == "running":
            try:
                audit = jobs.service.audit(identifier)
                job.stage = f"已完成 {len(audit.rounds)} 轮核验，继续处理证据" if audit.rounds else ("读取图像、生成回答与核验" if audit.parse_seconds else "解析 PDF")
            except FileNotFoundError:
                pass
        return job
    except FileNotFoundError as exc:
        raise HTTPException(404, "任务不存在。") from exc


@router.post("/jobs/{identifier}/retry", response_model=QuestionJob, status_code=202)
async def retry_job(identifier: UUID, jobs: QuestionJobs = Depends(get_jobs)) -> QuestionJob:
    try:
        return jobs.retry(identifier)
    except FileNotFoundError as exc:
        raise HTTPException(404, "任务不存在。") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/jobs/{identifier}/cancel", response_model=QuestionJob)
async def cancel_job(identifier: UUID, jobs: QuestionJobs = Depends(get_jobs)) -> QuestionJob:
    try:
        return await jobs.cancel(identifier)
    except FileNotFoundError as exc:
        raise HTTPException(404, "任务不存在。") from exc


@router.get("/questions/{identifier}/audit", response_model=QuestionAudit)
def get_audit(identifier: UUID, service: QuestionAnswerService = Depends(get_question_service)) -> QuestionAudit:
    try:
        return service.audit(identifier)
    except FileNotFoundError as exc:
        raise HTTPException(404, "审计尚未生成或任务不存在。") from exc


@router.get("/questions/{identifier}/pages/{page}")
def get_page(identifier: UUID, page: int, evidence_id: str | None = Query(None),
             service: QuestionAnswerService = Depends(get_question_service)) -> FileResponse:
    try:
        return FileResponse(service.page(identifier, page, evidence_id), media_type="image/png")
    except FileNotFoundError as exc:
        raise HTTPException(404, "任务或证据不存在。") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/questions", response_model=AnswerResponse)
async def ask_question(file: UploadFile = File(...), request: QuestionRequest = Depends(parse_request),
                       jobs: QuestionJobs = Depends(get_jobs)) -> AnswerResponse:
    import asyncio
    content = await file.read(30 * 1024 * 1024 + 1)
    try:
        job = jobs.submit(filename=file.filename or "", content=content, request=request)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await asyncio.shield(jobs.tasks[job.id])
    current = jobs.service.store.get(job.id)
    if current.status != "completed":
        raise HTTPException(504 if current.status == "timed_out" else 409, current.error or "任务未完成。")
    return jobs.service.get(job.id)


@router.get("/questions/{identifier}", response_model=AnswerResponse)
def get_answer(identifier: UUID, service: QuestionAnswerService = Depends(get_question_service)) -> AnswerResponse:
    try:
        return service.get(identifier)
    except FileNotFoundError as exc:
        raise HTTPException(404, "问答结果不存在或尚未完成。") from exc
