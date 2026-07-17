import io
import unittest

from paper_analysis.services.job_logging import TimestampedLogWriter


class TimestampedLogWriterTest(unittest.TestCase):
    def test_write_and_flush_open_stream(self) -> None:
        stream = io.StringIO()
        writer = TimestampedLogWriter(stream)

        writer.write("第一行\n第二行\n")
        writer.flush()

        output = stream.getvalue()
        self.assertIn("第一行", output)
        self.assertIn("第二行", output)

    def test_flush_on_closed_stream_does_not_raise(self) -> None:
        stream = io.StringIO()
        writer = TimestampedLogWriter(stream)
        writer.write("残留缓冲")

        stream.close()

        writer.flush()  # 不应抛 ValueError
        writer.write("关闭后写入")  # 同样静默

    def test_emit_on_closed_stream_does_not_raise(self) -> None:
        stream = io.StringIO()
        writer = TimestampedLogWriter(stream)
        writer.write("第一行\n")
        stream.close()

        writer.write("第二行\n")
        writer.flush()


if __name__ == "__main__":
    unittest.main()
