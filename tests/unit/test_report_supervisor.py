from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.domain.enums import AnalysisMode, DocumentKind, JobStatus
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.job_service import JobService
from paper_analysis.services.report_jobs import ProcessJobExecutor


class ReportSupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.service = JobService(job_store=LocalFilesystemJobStore(base_dir=root / "store"),
            artifact_service=ArtifactService(storage=LocalFilesystemArtifactStorage()),
            analysis_service=None, workspace_root=root / "workspace")
        self.executor = ProcessJobExecutor()

    async def asyncTearDown(self) -> None:
        await self.executor.close()
        self.temp.cleanup()

    async def new_job(self):
        return await self.service.create_job_from_upload(filename="synthetic.txt", content=b"synthetic",
            mode=AnalysisMode.GENERAL_TEXT, document_kind=DocumentKind.PLAIN_TEXT)

    async def test_cancel_reaps_real_child_and_retry_rejects_duplicate(self) -> None:
        job = await self.new_job()
        original_spawn = asyncio.create_subprocess_exec
        started = asyncio.Event()
        children = []

        async def spawn(*args, **kwargs):
            child = await original_spawn(args[0], "-c", "import time; time.sleep(30)", **kwargs)
            children.append(child)
            started.set()
            return child

        with patch("asyncio.create_subprocess_exec", side_effect=spawn):
            await self.executor.submit_job(job_service=self.service, job_id=job.id)
            await asyncio.wait_for(started.wait(), 5)
            await self.executor.cancel(job.id)
            self.assertIsNotNone(children[0].returncode)
            self.assertEqual((await self.service.get_job(job.id)).status, JobStatus.CANCELLED)
            retried = await self.executor.retry(job.id)
            self.assertEqual(retried.attempt, 2)
            with self.assertRaises(ValueError):
                await self.executor.retry(job.id)
            await self.executor.cancel(job.id)

    async def test_restart_marks_interrupted_attempt_failed(self) -> None:
        job = await self.new_job()
        job.status = JobStatus.ANALYZING
        await self.service._job_store.save(job)
        await self.executor.start(self.service)
        restored = await self.service.get_job(job.id)
        self.assertEqual(restored.status, JobStatus.FAILED)
        self.assertIn("重启", restored.error_message)

    async def test_timeout_reaps_real_child(self) -> None:
        job = await self.new_job()
        job.policy.effective.timeout_seconds = 0.05
        await self.service._job_store.save(job)
        original_spawn = asyncio.create_subprocess_exec
        children = []

        async def spawn(*args, **kwargs):
            child = await original_spawn(args[0], "-c", "import time; time.sleep(30)", **kwargs)
            children.append(child)
            return child

        with patch("asyncio.create_subprocess_exec", side_effect=spawn):
            await self.executor.submit_job(job_service=self.service, job_id=job.id)
            await self.executor.tasks[job.id]
        self.assertEqual((await self.service.get_job(job.id)).status, JobStatus.TIMED_OUT)
        self.assertIsNotNone(children[0].returncode)

    async def test_stale_result_cannot_publish(self) -> None:
        job = await self.new_job()
        result = job.model_copy(deep=True)
        result.attempt = 99
        directory = self.service._job_workspace(job.id)
        (directory / "result-1.json").write_text(result.model_dump_json())
        original_spawn = asyncio.create_subprocess_exec

        async def spawn(*args, **kwargs):
            return await original_spawn(args[0], "-c", "pass", **kwargs)

        with patch("asyncio.create_subprocess_exec", side_effect=spawn):
            await self.executor.submit_job(job_service=self.service, job_id=job.id)
            await self.executor.tasks[job.id]
        self.assertEqual((await self.service.get_job(job.id)).status, JobStatus.FAILED)
