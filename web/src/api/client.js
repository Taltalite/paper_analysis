const API_BASE_URL = __PAPER_ANALYSIS_API_BASE_URL__;

export const qaAssetUrl = (id, suffix) => `${API_BASE_URL}/api/qa/questions/${id}/${suffix}`;
export const listQuestionJobs = () => fetch(`${API_BASE_URL}/api/qa/jobs`).then(parseJsonResponse);
export const getQuestionJob = (id) => fetch(`${API_BASE_URL}/api/qa/jobs/${id}`).then(parseJsonResponse);
export const getQuestionAnswer = (id) => fetch(`${API_BASE_URL}/api/qa/questions/${id}`).then(parseJsonResponse);
export const retryQuestionJob = (id) => fetch(`${API_BASE_URL}/api/qa/jobs/${id}/retry`, { method: "POST" }).then(parseJsonResponse);
export const cancelQuestionJob = (id) => fetch(`${API_BASE_URL}/api/qa/jobs/${id}/cancel`, { method: "POST" }).then(parseJsonResponse);
export const submitQuestionJob = (data) => fetch(`${API_BASE_URL}/api/qa/jobs`, { method: "POST", body: data }).then(parseJsonResponse);

export async function askPaperQuestion(formData) {
  return parseJsonResponse(await fetch(`${API_BASE_URL}/api/qa/questions`, {
    method: "POST", body: formData,
  }));
}

async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(detail || "请求失败。");
  }
  return payload;
}

export async function createAnalysisJob(file, mode = "research_paper", policy = {}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mode", mode);
  Object.entries(policy).forEach(([key, value]) => formData.append(key, String(value)));

  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs`, {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse(response);
}

export async function getAnalysisJob(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}`);
  return parseJsonResponse(response);
}

export async function getAnalysisProgress(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}/progress`);
  return parseJsonResponse(response);
}

export async function getMarkdownReport(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}/report`);
  return parseJsonResponse(response);
}

export async function getArtifactContent(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}/artifact`);
  return parseJsonResponse(response);
}

export const createConversation = id => fetch(`${API_BASE_URL}/api/qa/questions/${id}/conversation`, { method: "POST" }).then(parseJsonResponse);
export const submitFollowup = (id, question) => fetch(`${API_BASE_URL}/api/qa/conversations/${id}/turns`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(question) }).then(parseJsonResponse);
export const cancelReport = id => fetch(`${API_BASE_URL}/api/analysis/jobs/${id}/cancel`, { method: "POST" }).then(parseJsonResponse);
export const retryReport = id => fetch(`${API_BASE_URL}/api/analysis/jobs/${id}/retry`, { method: "POST" }).then(parseJsonResponse);
