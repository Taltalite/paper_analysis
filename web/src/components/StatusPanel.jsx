const STATUS_LABELS = {
  pending: "排队中",
  parsing: "解析中",
  analyzing: "分析中",
  completed: "已完成",
  failed: "失败",
};

export default function StatusPanel({ job, error, modeLabel }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>任务状态</h2>
      </div>
      {job ? (
        <dl className="status-grid">
          <div>
            <dt>任务 ID</dt>
            <dd>{job.id}</dd>
          </div>
          <div>
            <dt>状态</dt>
            <dd className={`status status-${job.status}`}>{STATUS_LABELS[job.status] || job.status}</dd>
          </div>
          <div>
            <dt>文件</dt>
            <dd>{job.filename}</dd>
          </div>
          <div>
            <dt>模式</dt>
            <dd>{modeLabel ? modeLabel(job.mode) : job.mode}</dd>
          </div>
          <div>
            <dt>更新时间</dt>
            <dd>{new Date(job.updated_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt>错误信息</dt>
            <dd>{job.error_message || "无"}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted">尚未提交任务。</p>
      )}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
