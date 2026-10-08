export default function ExecutionControls({ disabled = false, report = false }) {
  return <fieldset disabled={disabled}>
    <legend>分析策略与预算</legend>
    <label>分析强度 <select name="intensity" defaultValue="standard">
      <option value="light">轻量</option><option value="standard">标准</option><option value="deep">深入</option>
    </select></label>
    <label>累计 token 预算 <input name="token_budget" type="number" min="256" max="120000" defaultValue="30000" required /></label>
    <label>调用上限 <input name="max_calls" type="number" min="1" max="128" defaultValue="16" required /></label>
    <label>单次输出上限 <input name="max_output_tokens" type="number" min="64" max="12000" defaultValue="4096" required /></label>
    <label>执行时限（秒）<input name="timeout_seconds" type="number" min="1" max="900" defaultValue="420" required /></label>
    {report && <label>报告补证据轮数 <select name="report_followups" defaultValue="1">
      <option value="0">不补取</option><option value="1">最多一轮</option><option value="2">最多两轮</option>
    </select></label>}
    <small>深入分析不会自动增加你填写的额度；估算用量不等同于实际账单。</small>
  </fieldset>;
}

export function executionOptions(data) {
  const result = {};
  for (const key of ["intensity", "token_budget", "max_calls", "max_output_tokens", "timeout_seconds", "report_followups"]) {
    if (data.has(key)) result[key] = key === "intensity" ? data.get(key) : Number(data.get(key));
  }
  return result;
}
