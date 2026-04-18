from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from uuid import UUID

from paper_analysis.services.job_service import JobService


logger = logging.getLogger(__name__)


class InProcessJobExecutor:
    def __init__(self, *, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="paper-analysis-job",
        )
        self._lock = Lock()
        self._futures: dict[UUID, Future[None]] = {}

    async def submit_job(self, *, job_service: JobService, job_id: UUID) -> None:
        with self._lock:
            current = self._futures.get(job_id)
            if current is not None and not current.done():
                return

            future = self._executor.submit(self._run_job, job_service, job_id)
            self._futures[job_id] = future
            future.add_done_callback(
                lambda completed, target_job_id=job_id: self._finalize_job(target_job_id, completed)
            )

    def _finalize_job(self, job_id: UUID, future: Future[None]) -> None:
        with self._lock:
            current = self._futures.get(job_id)
            if current is future:
                self._futures.pop(job_id, None)

        exc = future.exception()
        if exc is not None:
            logger.error("任务执行线程异常退出。job_id=%s error=%s", job_id, exc)

    @staticmethod
    def _run_job(job_service: JobService, job_id: UUID) -> None:
        asyncio.run(job_service.run_job(job_id))
