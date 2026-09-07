# Paper v1 人工标注模板

每篇论文只需确认 8--12 条最重要的可核验主张；不需要逐字标注全文。

## 标注规则

- `statement`：使用简洁的中文表述，保留模型名、数据集、指标和数值原文。
- `source_locator`：写页码、章节名和足以人工复查的短定位说明；不要把大段原文复制进仓库。
- `expected_verdict`：优先标记 `supported`；也至少各加入一条 `partially_supported`、`unsupported` 或 `conflicting` 的受控测试主张。
- `importance`：仅使用 `critical`、`major`、`minor`；第一版重点标 `critical` 和 `major`。
- 图表事实只能描述可直接观察或由 caption/正文明确支持的内容。

## 1. MoDorado

- case_id：`paper_v1_modorado`
- DOI：`10.1093/nar/gkaf795`

| claim_id | statement | source_locator（页码 / 章节 / 定位） | expected_verdict | importance | 已确认 |
|---|---|---|---|---|---|
| modorado-01 |  |  | supported | critical |  |
| modorado-02 |  |  | supported | major |  |
| modorado-negative-01 |  |  | unsupported / conflicting | major |  |

## 2. Three decades of nanopore sequencing

- case_id：`paper_v1_nanopore_review`
- DOI：`10.1038/nature16996`

| claim_id | statement | source_locator（页码 / 章节 / 定位） | expected_verdict | importance | 已确认 |
|---|---|---|---|---|---|
| review-01 |  |  | supported | critical |  |
| review-02 |  |  | supported | major |  |
| review-negative-01 |  |  | unsupported / conflicting | major |  |

## 3. Composite Hedges Nanopores codec system

- case_id：`paper_v1_composite_hedges`
- DOI：`10.1038/s41467-024-53455-3`

| claim_id | statement | source_locator（页码 / 章节 / 定位） | expected_verdict | importance | 已确认 |
|---|---|---|---|---|---|
| hedges-01 |  |  | supported | critical |  |
| hedges-02 |  |  | supported | major |  |
| hedges-negative-01 |  |  | unsupported / conflicting | major |  |

## 4. Dynamic-decision random access of DNA storage

- case_id：`paper_v1_dynamic_random_access`
- DOI：`10.1038/s41467-025-64293-2`

| claim_id | statement | source_locator（页码 / 章节 / 定位） | expected_verdict | importance | 已确认 |
|---|---|---|---|---|---|
| random-access-01 |  |  | supported | critical |  |
| random-access-02 |  |  | supported | major |  |
| random-access-negative-01 |  |  | unsupported / conflicting | major |  |

## 交付检查

- [ ] 每篇至少 8 条核心主张，且总计至少 32 条。
- [ ] 每篇至少 1 条可用于检验“待核验”渲染策略的负例。
- [ ] 每条主张都有可人工复查的 `source_locator`。
- [ ] 至少 4 篇论文中各选择 1 个关键 figure，记录图号和 2--3 条直接事实。
