import { test, expect } from '@playwright/test';

test('报告上传策略、取消、重试及刷新恢复来自后端', async ({ page }) => {
  let status = 'pending';
  let submitted = '';
  const job = () => ({ id: 'report-1', status, filename: 'synthetic.txt', mode: 'research_paper', updated_at: new Date().toISOString() });
  await page.route(/\/api\/(qa|analysis)\//, async route => {
    const path = new URL(route.request().url()).pathname;
    let body = [];
    if (path === '/api/analysis/jobs') { submitted = route.request().postData(); body = job(); }
    if (path.endsWith('/cancel')) { status = 'cancelled'; body = job(); }
    if (path.endsWith('/retry')) { status = 'pending'; body = job(); }
    if (path.endsWith('/progress')) body = { job: job(), progress_percent: 0, current_stage: '排队', steps: [], recent_logs: [] };
    await route.fulfill({ json: body });
  });
  await page.goto('/');
  const form = page.locator('form').filter({ has: page.getByRole('button', { name: '上传并分析' }) });
  await form.getByLabel('源文档').setInputFiles({ name: 'synthetic.txt', mimeType: 'text/plain', buffer: Buffer.from('synthetic') });
  await form.getByLabel('累计 token 预算').fill('6000');
  await form.getByLabel('分析强度').selectOption('deep');
  await form.getByRole('button', { name: '上传并分析' }).click();
  await expect(page.getByRole('button', { name: '取消报告' })).toBeVisible();
  expect(submitted).toContain('6000'); expect(submitted).toContain('deep');
  await page.getByRole('button', { name: '取消报告' }).click();
  await expect(page.getByRole('button', { name: '重试报告' })).toBeVisible();
  await page.getByRole('button', { name: '重试报告' }).click();
  await expect(page.getByRole('button', { name: '取消报告' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: '取消报告' })).toBeVisible();
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test('连续追问只发送 JSON 并保留预算用量未知提示', async ({ page }) => {
  let followup;
  let uploadCount = 0;
  const job = { id: 'q1', status: 'completed', stage: '完成', attempt: 1, filename: 'synthetic.pdf', request: { question: '重复数？' } };
  await page.route(/\/api\/(qa|analysis)\//, async route => {
    const path = new URL(route.request().url()).pathname;
    let body = {};
    if (path === '/api/qa/jobs') { body = [job]; if (route.request().method() === 'POST') uploadCount++; }
    else if (path.endsWith('/conversation')) body = { id: 'conversation-1' };
    else if (path.endsWith('/turns')) { followup = route.request().postDataJSON(); body = { ...job, id: 'q2', status: 'queued' }; }
    else if (path.includes('/jobs/')) body = { ...job, id: path.split('/').pop() };
    else body = { id: path.split('/').pop(), status: 'answered', answer: '三个重复', claims: [], evidence: [], uncertainties: [],
      visual_status: 'not_requested', followups: 0, execution: { actual_usage: { total: null }, unknown_usage: true, call_count: 1, cache_hits: 0, stop_reason: 'completed' } };
    await route.fulfill({ json: body });
  });
  await page.goto('/?qa=q1');
  await expect(page.getByText('实际已知 token：未记录', { exact: false })).toBeVisible();
  await page.getByLabel('同篇追问').fill('对照是什么？');
  await page.getByRole('button', { name: '继续追问（复用文档与预算）' }).click();
  await expect(page).toHaveURL(/qa=q2/);
  expect(followup.question).toBe('对照是什么？');
  expect(uploadCount).toBe(0);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});
