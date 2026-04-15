export default function StatusPanel({ job, error }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Job Status</h2>
      </div>
      {job ? (
        <dl className="status-grid">
          <div>
            <dt>Job ID</dt>
            <dd>{job.id}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd className={`status status-${job.status}`}>{job.status}</dd>
          </div>
          <div>
            <dt>File</dt>
            <dd>{job.filename}</dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd>{job.mode}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{new Date(job.updated_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt>Error</dt>
            <dd>{job.error_message || "None"}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted">No job submitted yet.</p>
      )}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
