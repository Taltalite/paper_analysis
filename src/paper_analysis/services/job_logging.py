from __future__ import annotations

import io
import logging
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Iterator


class TimestampedLogWriter(io.TextIOBase):
    def __init__(self, stream: io.TextIOBase) -> None:
        self._stream = stream
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""
        self._stream.flush()

    def isatty(self) -> bool:
        return False

    def _emit(self, line: str) -> None:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        self._stream.write(f"{timestamp} {line}\n")


@contextmanager
def capture_job_logs(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    original_level = root_logger.level
    with path.open("a", encoding="utf-8") as raw_stream:
        writer = TimestampedLogWriter(raw_stream)
        handler = logging.StreamHandler(writer)
        handler.setLevel(logging.INFO)
        root_logger.addHandler(handler)
        if root_logger.level > logging.INFO:
            root_logger.setLevel(logging.INFO)
        writer.write("开始记录任务日志。\n")
        writer.flush()
        try:
            with redirect_stdout(writer), redirect_stderr(writer):
                yield
        finally:
            handler.flush()
            root_logger.removeHandler(handler)
            root_logger.setLevel(original_level)
            writer.write("任务日志记录结束。\n")
            writer.flush()
