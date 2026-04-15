import { useEffect, useRef, useState } from "react";

import { createAnalysisJob, getAnalysisJob, getArtifactContent, getMarkdownReport } from "../api/client";
import ReportPanel from "../components/ReportPanel";
import StatusPanel from "../components/StatusPanel";

const POLL_INTERVAL_MS = 2000;
const MODE = "research_paper";

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function modeLabel(mode) {
  if (mode === "research_paper") {
    return "研究型文献分析";
  }
  if (mode === "general_text") {
    return "通用文本分析";
  }
  return mode;
}

export default function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  const [artifacts, setArtifacts] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  async function refreshCompletedArtifacts(jobId) {
    const [reportPayload, artifactPayload] = await Promise.all([
      getMarkdownReport(jobId),
      getArtifactContent(jobId),
    ]);
    setReport(reportPayload);
    setArtifacts(artifactPayload);
  }

  function stopPolling() {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling(jobId) {
    stopPolling();
    pollRef.current = window.setInterval(async () => {
      try {
        const latest = await getAnalysisJob(jobId);
        setJob(latest);
        if (latest.status === "completed") {
          stopPolling();
          await refreshCompletedArtifacts(jobId);
        }
        if (latest.status === "failed") {
          stopPolling();
          setError(latest.error_message || "分析任务失败。");
        }
      } catch (requestError) {
        stopPolling();
        setError(requestError.message);
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selectedFile) {
      setError("请先选择一个 PDF、TXT 或 MD 文件。");
      return;
    }

    setSubmitting(true);
    setError("");
    setJob(null);
    setReport(null);
    setArtifacts(null);

    try {
      const createdJob = await createAnalysisJob(selectedFile, MODE);
      setJob(createdJob);
      startPolling(createdJob.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="layout">
      <section className="hero panel">
        <div className="panel-header">
          <h1>论文分析系统</h1>
        </div>
        <p className="hero-copy">
          上传 PDF 或文本文件，提交到后端统一分析接口，并查看生成的 markdown 报告。
        </p>
        <form className="upload-form" onSubmit={handleSubmit}>
          <label className="file-input">
            <span>源文档</span>
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "提交中..." : "上传并分析"}
          </button>
        </form>
      </section>

      <StatusPanel job={job} error={error} modeLabel={modeLabel} />

      <section className="panel">
        <div className="panel-header">
          <h2>下载结果</h2>
        </div>
        {artifacts ? (
          <div className="download-row">
            <button
              type="button"
              onClick={() =>
                downloadTextFile(`${job.filename}.report.md`, artifacts.markdown_report, "text/markdown")
              }
            >
              下载 Markdown
            </button>
            <button
              type="button"
              onClick={() =>
                downloadTextFile(
                  `${job.filename}.report.json`,
                  JSON.stringify(artifacts.json_report, null, 2),
                  "application/json",
                )
              }
            >
              下载 JSON
            </button>
            {artifacts.parsed_markdown ? (
              <button
                type="button"
                onClick={() =>
                  downloadTextFile(`${job.filename}.parsed.md`, artifacts.parsed_markdown, "text/markdown")
                }
              >
                下载结构化 Markdown
              </button>
            ) : null}
          </div>
        ) : (
          <p className="muted">任务完成后可下载 Markdown、JSON 和结构化解析结果。</p>
        )}
      </section>

      <ReportPanel report={report} />
    </main>
  );
}
