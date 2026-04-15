import ReactMarkdown from "react-markdown";

export default function ReportPanel({ report }) {
  return (
    <section className="panel report-panel">
      <div className="panel-header">
        <h2>Markdown Report</h2>
      </div>
      {report ? (
        <div className="markdown-body">
          <ReactMarkdown>{report.markdown_report}</ReactMarkdown>
        </div>
      ) : (
        <p className="muted">The report will appear here after the job completes.</p>
      )}
    </section>
  );
}
