from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from paper_analysis.api.deps import get_job_service
from paper_analysis.domain.enums import AnalysisMode, DocumentKind
from paper_analysis.domain.schemas import AnalysisJob, ArtifactContentResponse, MarkdownReportResponse
from paper_analysis.services.job_service import JobService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/jobs", response_model=AnalysisJob, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: AnalysisMode = Form(default=AnalysisMode.RESEARCH_PAPER),
    job_service: JobService = Depends(get_job_service),
) -> AnalysisJob:
    filename = file.filename or "uploaded.bin"
    document_kind = _document_kind_for(filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    job = await job_service.create_job_from_upload(
        filename=filename,
        content=content,
        mode=mode,
        document_kind=document_kind,
    )
    background_tasks.add_task(job_service.run_job, job.id)
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
        detail="Unsupported file type. Use .pdf, .txt, or .md.",
    )
