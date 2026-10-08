export default function ResearchProducts({ products }) {
  if (!products) return null;
  const roles = { problem: "研究问题", hypothesis: "假设", design: "设计", result: "结果", conclusion: "结论", limitation: "局限" };
  return <section className="panel">
    <h2>论文故事、图组与比较结果</h2>
    <p>已核验主张 {products.coverage.verified.claims.length}/{products.coverage.candidate.claims.length}；
      选择图表 {products.coverage.selected.figures.length}/{products.coverage.candidate.figures.length}</p>
    <h3>故事架构</h3>
    <ol>{products.story.nodes.map(node => <li key={node.node_id}>{roles[node.role]}：{node.statement}<small>（{node.evidence_ids.join("、")}）</small></li>)}</ol>
    {!products.story.nodes.length && <p>当前没有可交付的故事节点。</p>}
    <h3>图组 flow</h3>
    <ul>{products.figure_flow.nodes.map(node => <li key={node.node_id}>{node.figure} {node.panel || ""}：{node.role}（{node.coverage_status}）</li>)}</ul>
    <ul>{products.figure_flow.edges.map(edge => <li key={edge.edge_id}>{edge.source} → {edge.target}：{edge.relation}（{edge.evidence_ids.join("、")}）</li>)}</ul>
    {!products.figure_flow.edges.length && <p>尚无通过核验的图间论证关系。</p>}
    <h3>Benchmark</h3>
    {products.benchmark.status === "available" ? <table>
      <thead><tr><th>方法</th><th>数据集/切分</th><th>指标</th><th>结果</th><th>证据</th></tr></thead>
      <tbody>{products.benchmark.entries.map(row => <tr key={row.entry_id}><td>{row.method}</td><td>{row.dataset} / {row.split}</td><td>{row.metric} ({row.direction})</td><td>{row.value_raw} {row.unit}</td><td>{row.evidence_ids.join("、")}</td></tr>)}</tbody>
    </table> : <p>{products.benchmark.reason}</p>}
  </section>;
}
