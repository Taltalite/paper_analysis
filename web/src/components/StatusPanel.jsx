const STATUS_LABELS = {
  pending: "排队中",
  parsing: "解析中",
  analyzing: "分析中",
  completed: "已完成",
  failed: "失败",
};

const STEP_STATUS_LABELS = {
  pending: "待开始",
  active: "进行中",
  completed: "已完成",
  failed: "失败",
};

export default function StatusPanel({ job, progress, error, modeLabel, submitting, syncingStatus }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>任务状态</h2>
      </div>
      {job ? (
        <>
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

          {progress ? (
            <>
            <div className="progress-overview">
              <div>
                <span className="progress-label">当前阶段</span>
                <strong>{progress.current_stage}</strong>
              </div>
              <div>
                <span className="progress-label">阶段摘要</span>
                <strong>{progress.summary_message}</strong>
              </div>
              <div>
                <span className="progress-label">整体进度</span>
                <strong>{progress.progress_percent}%</strong>
              </div>
            </div>
            <div
              className="progress-bar"
              role="progressbar"
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={progress.progress_percent}
            >
              <div className="progress-bar-fill" style={{ width: `${progress.progress_percent}%` }} />
            </div>
            <div className="step-list">
              {progress.steps.map((step) => (
                <div key={step.key} className={`step-card step-${step.status}`}>
                  <span>{step.label}</span>
                  <strong>{STEP_STATUS_LABELS[step.status] || step.status}</strong>
                </div>
              ))}
            </div>
            <div className="log-panel">
              <div className="panel-header">
                <h3>实时日志</h3>
              </div>
              {progress.recent_logs.length ? (
                <pre className="log-output">{progress.recent_logs.join("\n")}</pre>
              ) : (
                <p className="muted">后端日志生成后会显示在这里。</p>
              )}
            </div>
            </>
          ) : null}
        </>
      ) : (
        <p className="muted">尚未提交任务。</p>
      )}
      {!job && submitting ? (
        <p className="muted">正在提交任务到后端，请稍候。</p>
      ) : null}
      {job && job.status !== "completed" && job.status !== "failed" ? (
        <p className="muted">
          {syncingStatus ? "前端正在同步后端状态，状态会在解析和分析阶段实时更新。" : "任务已提交，等待下一次状态同步。"}
        </p>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
