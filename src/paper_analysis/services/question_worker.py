"""本地队列子进程入口；领域编排由 service/pipeline 负责。"""
import sys
import os
import signal
import ctypes
from pathlib import Path
from uuid import UUID

def main() -> None:
    parent = os.getppid()
    ctypes.CDLL(None).prctl(1, signal.SIGKILL)
    if parent == 1 or os.getppid() != parent:
        raise SystemExit(1)
    from paper_analysis.services.question_answer_service import build_question_answer_service
    service = build_question_answer_service(Path(sys.argv[1]), disable_vision=len(sys.argv) > 4 and sys.argv[4] == "no-vision")
    service.execute(UUID(sys.argv[2]), int(sys.argv[3]))


if __name__ == "__main__":
    main()
