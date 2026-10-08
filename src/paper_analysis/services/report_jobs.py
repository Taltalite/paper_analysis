"""报告进程主管：worker 写 attempt 产物，父进程验证后发布。"""
from __future__ import annotations

import asyncio
import fcntl
import os
import signal
import sys
from uuid import UUID

from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.enums import JobStatus
from paper_analysis.domain.schemas import AnalysisJob


class ProcessJobExecutor:
    def __init__(self, concurrency: int = 2) -> None:
        self.concurrency = concurrency
        self.tasks: dict[UUID, asyncio.Task] = {}
        self.lock = None
        self.start_lock = asyncio.Lock()
        self.retry_lock = asyncio.Lock()
        self.service = None

    async def start(self, service) -> None:
        async with self.start_lock:
            if self.lock:
                return
            self.service = service
            service._workspace_root.mkdir(parents=True, exist_ok=True)
            self.lock = (service._workspace_root / "supervisor.lock").open("a")
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock.close()
                self.lock = None
                raise RuntimeError("报告队列仅支持一个 API 主管。")
            self.semaphore = asyncio.Semaphore(self.concurrency)
            for job in await service._job_store.list():
                if job.status in {JobStatus.PARSING, JobStatus.ANALYZING}:
                    job.status, job.error_message = JobStatus.FAILED, "服务重启，旧报告尝试已中断，可重试。"
                    await service._job_store.save(job)
                    from paper_analysis.runtime.budget import seal_interrupted_budget
                    seal_interrupted_budget(service._job_workspace(job.id) / "budget.json", "interrupted")
                elif job.status == JobStatus.PENDING:
                    self._schedule(job)

    async def submit_job(self, *, job_service, job_id: UUID) -> None:
        await self.start(job_service)
        if job_id not in self.tasks:
            job = await job_service.get_job(job_id)
            if job.status == JobStatus.PENDING:
                self._schedule(job)

    def _schedule(self, job: AnalysisJob) -> None:
        self.tasks[job.id] = asyncio.create_task(self._run(job))

    async def _run(self, job: AnalysisJob) -> None:
        process = None
        status, error = None, None
        try:
            async with self.semaphore:
                current = await self.service.get_job(job.id)
                if current.attempt != job.attempt or current.status != JobStatus.PENDING:
                    return
                directory = self.service._job_workspace(job.id)
                timeout = job.policy.effective.timeout_seconds if job.policy else 600
                spawning = asyncio.create_task(asyncio.create_subprocess_exec(sys.executable, "-m", "paper_analysis.services.report_worker",
                    str(self.service._job_store._base_dir.resolve()), str(self.service._workspace_root.resolve()),
                    str(job.id), str(job.attempt), stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL, start_new_session=True))
                try:
                    process = await asyncio.shield(spawning)
                except asyncio.CancelledError:
                    process = await spawning
                    raise
                await asyncio.wait_for(process.wait(), timeout)
                if process.returncode:
                    raise RuntimeError("报告子进程失败。")
                result = AnalysisJob.model_validate_json((directory / f"result-{job.attempt}.json").read_text())
                current = await self.service.get_job(job.id)
                if current.attempt != job.attempt or current.status not in {JobStatus.PARSING, JobStatus.ANALYZING, JobStatus.PENDING}:
                    return
                if result.id != job.id or result.document_sha256 != job.document_sha256 or result.attempt != job.attempt:
                    raise ValueError("报告产物绑定不匹配。")
                result.status = JobStatus.COMPLETED
                await self.service._job_store.save(result)
        except asyncio.TimeoutError:
            status, error = JobStatus.TIMED_OUT, "报告执行超时，工作进程已终止。"
        except asyncio.CancelledError:
            status, error = JobStatus.CANCELLED, "报告已取消。"
        except Exception:
            status, error = JobStatus.FAILED, "报告执行失败，请查看本次审计或重试。"
        finally:
            if process is not None and process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
            if status:
                from paper_analysis.runtime.budget import seal_interrupted_budget
                seal_interrupted_budget(self.service._job_workspace(job.id) / "budget.json", status.value)
                current = await self.service.get_job(job.id)
                if current.attempt == job.attempt:
                    current.status, current.error_message = status, error
                    await self.service._job_store.save(current)
            if self.tasks.get(job.id) is asyncio.current_task():
                self.tasks.pop(job.id, None)

    async def cancel(self, identifier: UUID):
        job = await self.service.get_job(identifier)
        task = self.tasks.get(identifier)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if self.tasks.get(identifier) is task:
                self.tasks.pop(identifier, None)
            # 排队任务尚未进入 coroutine 时也必须完成状态转换。
            job = await self.service.get_job(identifier)
            if job.status in {JobStatus.PENDING, JobStatus.PARSING, JobStatus.ANALYZING}:
                job.status = JobStatus.CANCELLED
                await self.service._job_store.save(job)
        return await self.service.get_job(identifier)

    async def retry(self, identifier: UUID):
        async with self.retry_lock:
            return await self._retry_locked(identifier)

    async def _retry_locked(self, identifier: UUID):
        job = await self.service.get_job(identifier)
        if job.status not in {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMED_OUT}:
            raise ValueError("仅失败、取消或超时任务可重试。")
        job.attempt += 1
        job.status, job.error_message = JobStatus.PENDING, None
        await self.service._job_store.save(job)
        self._schedule(job)
        return job

    async def close(self) -> None:
        for task in list(self.tasks.values()):
            task.cancel()
        await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)
        self.tasks.clear()
        if self.lock:
            self.lock.close()
            self.lock = None
