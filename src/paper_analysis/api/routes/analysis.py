from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from paper_analysis.api.deps import get_job_executor, get_job_service
from paper_analysis.domain.enums import AnalysisMode, DocumentKind
from paper_analysis.domain.schemas import (
    AnalysisJob,
    ArtifactContentResponse,
    JobProgressResponse,
    MarkdownReportResponse,
)
from paper_analysis.services.job_executor import InProcessJobExecutor
from paper_analysis.services.job_service import JobService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/jobs", response_model=AnalysisJob, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    file: UploadFile = File(...),
    mode: AnalysisMode = Form(default=AnalysisMode.RESEARCH_PAPER),
    job_service: JobService = Depends(get_job_service),
    job_executor: InProcessJobExecutor = Depends(get_job_executor),
) -> AnalysisJob:
    filename = file.filename or "uploaded.bin"
    document_kind = _document_kind_for(filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件不能为空。")

    job = await job_service.create_job_from_upload(
        filename=filename,
        content=content,
        mode=mode,
        document_kind=document_kind,
    )
    await job_executor.submit_job(job_service=job_service, job_id=job.id)
    return job


@router.get("/jobs/{job_id}", response_model=AnalysisJob)
async def get_job(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> AnalysisJob:
    try:
        return await job_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> JobProgressResponse:
    try:
        return await job_service.get_job_progress(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/report", response_model=MarkdownReportResponse)
async def get_markdown_report(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> MarkdownReportResponse:
    try:
        return await job_service.get_markdown_report(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/artifact", response_model=ArtifactContentResponse)
async def get_artifact_content(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> ArtifactContentResponse:
    try:
        return await job_service.get_artifact_content(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _document_kind_for(filename: str) -> DocumentKind:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return DocumentKind.PDF
    if lowered.endswith(".txt") or lowered.endswith(".md"):
        return DocumentKind.PLAIN_TEXT
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="暂不支持该文件类型，请使用 .pdf、.txt 或 .md。",
    )
