import ReactMarkdown from "react-markdown";

export default function ReportPanel({ report }) {
  return (
    <section className="panel report-panel">
      <div className="panel-header">
        <h2>Markdown 报告</h2>
      </div>
      {report ? (
        <div className="markdown-body">
          <ReactMarkdown>{report.markdown_report}</ReactMarkdown>
        </div>
      ) : (
        <p className="muted">任务完成后，报告会显示在这里。</p>
      )}
    </section>
  );
}
