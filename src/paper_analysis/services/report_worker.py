"""可终止的报告进程入口，不承载领域逻辑。"""
import asyncio
import ctypes
import os
import signal
import sys
from pathlib import Path
from uuid import UUID


def main() -> None:
    parent = os.getppid()
    ctypes.CDLL(None).prctl(1, signal.SIGKILL)
    if parent == 1 or os.getppid() != parent:
        raise SystemExit(1)
    from paper_analysis.services.bootstrap import build_default_analysis_service, build_default_artifact_service
    from paper_analysis.services.job_service import JobService
    from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
    service = JobService(job_store=LocalFilesystemJobStore(base_dir=Path(sys.argv[1])),
        artifact_service=build_default_artifact_service(), analysis_service=build_default_analysis_service(),
        workspace_root=Path(sys.argv[2]))
    async def run() -> None:
        job = await service.get_job(UUID(sys.argv[3]))
        if job.attempt != int(sys.argv[4]):
            raise ValueError("报告 attempt 已过期。")
        await service.run_job(job.id, publish=False)
    asyncio.run(run())


if __name__ == "__main__":
    main()
