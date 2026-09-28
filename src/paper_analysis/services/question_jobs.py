"""单服务进程本地队列；工作子进程只写尝试产物，主管负责发布最终状态。"""
from __future__ import annotations

import asyncio
import fcntl
import os
import signal
import sys
from collections.abc import Awaitable, Callable
from uuid import UUID

from paper_analysis.domain.qa import AnswerResponse, QuestionJob, QuestionRequest
from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.services.question_answer_service import QuestionAnswerService


class QuestionJobs:
    def __init__(self, service: QuestionAnswerService, *, timeout: float = 600,
                 concurrency: int = 2, worker: Callable[[QuestionJob], Awaitable[AnswerResponse]] | None = None) -> None:
        self.service, self.timeout = service, timeout
        self.semaphore = asyncio.Semaphore(concurrency)
        self.worker = worker or self._subprocess
        self.tasks: dict[UUID, asyncio.Task] = {}
        self.lock = None

    async def start(self) -> None:
        self.service.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.service.root / "supervisor.lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            raise RuntimeError("问答队列仅支持一个 API 主管进程。")
        for job in self.service.store.list():
            if job.status == "running":
                job.status, job.stage, job.error = "failed", "执行中断", "服务重启，旧尝试不再发布；可重试。"
                self.service.store.save(job)
            elif job.status == "queued":
                self._schedule(job)

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.clear()
        if self.lock:
            self.lock.close()
            self.lock = None

    def submit(self, *, filename: str, content: bytes, request: QuestionRequest) -> QuestionJob:
        job = self.service.prepare(filename=filename, content=content, request=request)
        self._schedule(job)
        return job

    def retry(self, identifier: UUID) -> QuestionJob:
        job = self.service.store.get(identifier)
        if job.status not in {"failed", "timed_out", "cancelled"}:
            raise ValueError("仅失败、超时或已取消的任务可重试。")
        job.attempt += 1
        job.status, job.stage, job.error = "queued", "等待重试", None
        self.service.store.save(job)
        self._schedule(job)
        return job

    async def cancel(self, identifier: UUID) -> QuestionJob:
        job = self.service.store.get(identifier)
        if job.status in {"queued", "running"}:
            job.status, job.stage = "cancelled", "已取消"
            self.service.store.save(job)
            task = self.tasks.get(identifier)
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                if self.tasks.get(identifier) is task:
                    self.tasks.pop(identifier, None)
            self._seal_audit(job)
        return self.service.store.get(identifier)

    def _schedule(self, job: QuestionJob) -> None:
        self.tasks[job.id] = asyncio.create_task(self._run(job))

    async def _run(self, job: QuestionJob) -> None:
        try:
            async with self.semaphore:
                current = self.service.store.get(job.id)
                if current.attempt != job.attempt or current.status != "queued":
                    return
                job.status, job.stage = "running", "解析、读取证据与核验"
                self.service.store.save(job)
                response = await asyncio.wait_for(self.worker(job), timeout=self.timeout)
                self.service.complete(job, response)
        except asyncio.TimeoutError:
            self._fail(job, "timed_out", "执行超时，工作进程已终止，可重试。")
        except asyncio.CancelledError:
            self._fail(job, "cancelled", "执行已取消，可重试。")
        except Exception:
            self._fail(job, "failed", "解析或工作进程失败，详见本次审计记录。")
        finally:
            if self.tasks.get(job.id) is asyncio.current_task():
                self.tasks.pop(job.id, None)

    def _fail(self, job: QuestionJob, status: str, message: str) -> None:
        current = self.service.store.get(job.id)
        if current.attempt == job.attempt and current.status in {"running", "queued"}:
            current.status, current.error, current.stage = status, message, message
            self.service.store.save(current)
            self._seal_audit(current)

    def _seal_audit(self, job: QuestionJob) -> None:
        try:
            audit = self.service.audit(job.id)
            atomic_json(self.service.store.directory(job.id) / f"audit-{job.attempt}.json", audit)
        except FileNotFoundError:
            pass  # 排队期间取消，尚未开始运行。

    async def _subprocess(self, job: QuestionJob) -> AnswerResponse:
        process = await asyncio.create_subprocess_exec(sys.executable, "-m", "paper_analysis.services.question_worker",
            str(self.service.root), str(job.id), str(job.attempt),
            "no-vision" if self.service.vision_model is None else "vision", stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
        try:
            code = await process.wait()
            if code:
                raise RuntimeError("工作进程失败。")
        finally:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
        path = self.service.store.directory(job.id) / f"result-{job.attempt}.json"
        return AnswerResponse.model_validate_json(path.read_text())
