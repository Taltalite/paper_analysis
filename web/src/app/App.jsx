import { useEffect, useRef, useState } from "react";

import { createAnalysisJob, getAnalysisJob, getArtifactContent, getMarkdownReport } from "../api/client";
import ReportPanel from "../components/ReportPanel";
import StatusPanel from "../components/StatusPanel";

const POLL_INTERVAL_MS = 2000;

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
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
          setError(latest.error_message || "Analysis failed.");
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
      setError("Choose a PDF, TXT, or MD file first.");
      return;
    }

    setSubmitting(true);
    setError("");
    setJob(null);
    setReport(null);
    setArtifacts(null);

    try {
      const createdJob = await createAnalysisJob(selectedFile, "research_paper");
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
          <h1>Paper Analysis</h1>
        </div>
        <p className="hero-copy">
          Upload a PDF, submit it to the backend analysis job API, and review the generated markdown report.
        </p>
        <form className="upload-form" onSubmit={handleSubmit}>
          <label className="file-input">
            <span>Source document</span>
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Upload And Analyze"}
          </button>
        </form>
      </section>

      <StatusPanel job={job} error={error} />

      <section className="panel">
        <div className="panel-header">
          <h2>Downloads</h2>
        </div>
        {artifacts ? (
          <div className="download-row">
            <button
              type="button"
              onClick={() =>
                downloadTextFile(`${job.filename}.report.md`, artifacts.markdown_report, "text/markdown")
              }
            >
              Download Markdown
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
              Download JSON
            </button>
            {artifacts.parsed_markdown ? (
              <button
                type="button"
                onClick={() =>
                  downloadTextFile(`${job.filename}.parsed.md`, artifacts.parsed_markdown, "text/markdown")
                }
              >
                Download Parsed Markdown
              </button>
            ) : null}
          </div>
        ) : (
          <p className="muted">Downloads become available after the job completes.</p>
        )}
      </section>

      <ReportPanel report={report} />
    </main>
  );
}
