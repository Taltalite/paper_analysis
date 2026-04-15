const API_BASE_URL = __PAPER_ANALYSIS_API_BASE_URL__;

async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(detail || "请求失败。");
  }
  return payload;
}

export async function createAnalysisJob(file, mode = "research_paper") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mode", mode);

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

export async function getMarkdownReport(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}/report`);
  return parseJsonResponse(response);
}

export async function getArtifactContent(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/jobs/${jobId}/artifact`);
  return parseJsonResponse(response);
}
