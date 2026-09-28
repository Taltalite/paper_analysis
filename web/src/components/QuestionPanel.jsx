import { useEffect, useState } from "react";
import { submitQuestionJob, getQuestionJob, getQuestionAnswer, listQuestionJobs, retryQuestionJob, cancelQuestionJob, qaAssetUrl } from "../api/client";

const statuses = { answered: "已回答", partial: "部分回答", refused: "证据不足，拒答" };
const sources = { text: "正文", caption: "图注", vision: "页面视觉模型观察" };

export default function QuestionPanel() {
  const [answer, setAnswer] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [job, setJob] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [identifier, setIdentifier] = useState(() => new URLSearchParams(window.location.search).get("qa"));
  const [preview, setPreview] = useState(null);
  const busy = submitting || ["queued", "running"].includes(job?.status);
  function selectJob(id) {
    setIdentifier(id); setAnswer(null); setJob(null); setPreview(null); setError("");
    const url = new URL(window.location.href);
    url.searchParams.set("qa", id);
    window.history.replaceState(null, "", url);
  }
  useEffect(() => { listQuestionJobs().then(setJobs).catch(() => {}); }, [job?.status]);
  useEffect(() => {
    if (!identifier) return;
    let disposed = false;
    let timer;
    async function poll() {
      try {
        const value = await getQuestionJob(identifier);
        if (disposed) return;
        setJob(value);
        if (value.status === "completed") {
          const result = await getQuestionAnswer(identifier);
          if (!disposed) setAnswer(result);
        } else if (["queued", "running"].includes(value.status)) {
          timer = window.setTimeout(poll, 1500);
        }
      } catch (failure) { if (!disposed) setError(failure.message); }
    }
    poll();
    return () => { disposed = true; window.clearTimeout(timer); };
  }, [identifier, job?.attempt]);
  async function retry() {
    try { const next = await retryQuestionJob(identifier); setJob(next); setError(""); }
    catch (failure) { setError(failure.message); }
  }
  async function cancel() {
    try { setJob(await cancelQuestionJob(identifier)); }
    catch (failure) { setError(failure.message); }
  }
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSubmitting(true); setError(""); setAnswer(null);
    try { const created = await submitQuestionJob(data); selectJob(created.id); setJob(created); }
    catch (failure) { setError(failure.message); }
    finally { setSubmitting(false); }
  }
  return <section className="panel">
    <h2>生物信息与表观遗传学文献图表问答</h2>
    <p>上传单篇 PDF，直接提问，无需先生成全文报告。</p>
    <label>恢复后端任务 <select value={identifier || ""} onChange={e => selectJob(e.target.value)}>
      <option value="" disabled>选择最近的问答任务</option>
      {jobs.map(item => <option key={item.id} value={item.id}>{item.filename} · {item.request.question.slice(0, 35)}</option>)}
    </select></label>
    {job && <p role="status">{job.stage}（尝试 {job.attempt}）{job.error && `：${job.error}`}</p>}
    {job && ["failed", "timed_out", "cancelled"].includes(job.status) && <button onClick={retry}>重试此问题</button>}
    {job && ["queued", "running"].includes(job.status) && <button onClick={cancel}>取消任务</button>}
    <form className="upload-form" onSubmit={submit}>
      <label>论文 PDF <input name="file" type="file" accept=".pdf" required disabled={busy} /></label>
      <label>问题 <textarea name="question" required maxLength={2000} placeholder="该图是否支持染色质可及性发生变化？对照是什么？" disabled={busy} /></label>
      <label>图号（可选）<input name="figure" placeholder="例如 2" disabled={busy} /></label>
      <label>子图（可选）<input name="panel" placeholder="例如 a，需同时填写图号" maxLength={1} disabled={busy} /></label>
      <label>证据补取与纠错上限 <select name="max_followups" defaultValue="2" disabled={busy}>
        <option value="0">单轮问答</option><option value="1">最多一次</option><option value="2">最多两次</option>
      </select></label>
      <button disabled={busy}>{busy ? "正在读取证据并核验…" : "提交问题"}</button>
    </form>
    <div aria-live="polite">
      {error && <p role="alert">{error}</p>}
      {answer && <>
        <h3>{statuses[answer.status]}</h3>
        <p>{answer.visual_status === "succeeded" ? "已获得页面视觉证据" : answer.visual_status === "failed" ? "未能可靠读取目标图像" : "本次未读取图像"}；补取与纠错 {answer.followups} 次</p>
        {answer.claims.length ? <ol>{answer.claims.map(claim => <li key={claim.claim_id}>
          {claim.statement} <small>证据：{claim.evidence_ids.map(id => <button key={id} onClick={() => {
            const location = answer.evidence.find(item => item.evidence_id === id);
            if (location) setPreview({ page: location.page, id });
          }}>{id}</button>)}</small>
        </li>)}</ol> : <p>{answer.answer}</p>}
        <h3>证据定位</h3>
        {answer.evidence.map(item => <details key={item.evidence_id} id={`qa-evidence-${encodeURIComponent(item.evidence_id)}`}>
          <summary>{item.evidence_id} · {sources[item.kind]} · PDF 第 {item.page} 页 {item.figure} {item.panel && `子图 ${item.panel}`}</summary>
          {item.image_pages.length > 0 && <p>送入视觉模型的页面：{item.image_pages.join("、")}</p>}
          <blockquote>{item.excerpt}</blockquote>
          <button onClick={() => setPreview({ page: item.page, id: item.evidence_id })}>查看对应页与正文框</button>
          {item.image_pages.map(page => <button key={page} onClick={() => setPreview({ page, id: item.evidence_id })}>实际视觉输入：第 {page} 页</button>)}
        </details>)}
        {preview && <figure><figcaption>PDF 第 {preview.page} 页 · {preview.id}</figcaption>
          <img style={{ maxWidth: "100%" }} alt={`证据所在的 PDF 第 ${preview.page} 页`}
            src={qaAssetUrl(answer.id, `pages/${preview.page}?evidence_id=${encodeURIComponent(preview.id)}`)} />
        </figure>}
        <p><a href={qaAssetUrl(answer.id, "audit")} target="_blank" rel="noreferrer">查看本次证据与核验记录</a></p>
        <h3>不确定性</h3><ul>{answer.uncertainties.map((value, index) => <li key={index}>{value}</li>)}</ul>
        <p className="muted">{answer.validation_scope}</p>
      </>}
    </div>
  </section>;
}
