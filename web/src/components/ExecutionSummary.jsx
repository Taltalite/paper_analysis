const reasons = { completed: "处理完成", token_budget_exhausted: "token 预算不足", call_budget_exhausted: "达到调用上限",
  deadline_exceeded: "超过执行时限", no_new_evidence: "没有新增证据", round_limit: "达到纠错轮数",
  budget_exhausted: "达到本轮处理上限", cancelled: "已取消", running: "处理中" };
export default function ExecutionSummary({ policy, execution }) {
  if (!policy && !execution) return null;
  return <aside aria-label="执行用量">
    <h3>执行策略与用量</h3>
    {policy && <p>生效强度：{({ light: "轻量", standard: "标准", deep: "深入" })[policy.effective.intensity]}；
      token 预算：{policy.effective.token_budget}；调用上限：{policy.effective.max_calls}</p>}
    {execution && <p>实际已知 token：{execution.actual_usage?.total ?? "未记录"}；
      估算或预留：{execution.estimated_usage?.total ?? 0}；请求记录：{execution.call_count}；缓存命中：{execution.cache_hits}；
      {execution.unknown_usage ? "含未知用量，已保守预留；" : ""}
      状态：{reasons[execution.stop_reason] || execution.stop_reason}</p>}
    <small>费用未计算；阶段进度不代表实时 token 进度。重试和追问共享原有预算。</small>
  </aside>;
}
