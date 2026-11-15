import type {
  DashboardStats,
  FixSuggestion,
  HealthInfo,
  ReviewDetailResponse,
  ReviewStatusResponse,
  ReviewSummaryItem,
} from "../types/review";

const API_BASE = "/api";

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) detail = String(err.detail);
    } catch {
      // ignore non-json error body
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch(`${API_BASE}/health`);
  return handleJson<HealthInfo>(res);
}

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/stats`);
  return handleJson<DashboardStats>(res);
}

export async function fetchReviews(): Promise<ReviewSummaryItem[]> {
  const res = await fetch(`${API_BASE}/reviews`);
  return handleJson<ReviewSummaryItem[]>(res);
}

export async function fetchReviewDetail(reviewId: string): Promise<ReviewDetailResponse> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}`);
  return handleJson<ReviewDetailResponse>(res);
}

export async function fetchReviewStatus(reviewId: string): Promise<ReviewStatusResponse> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/status`);
  return handleJson<ReviewStatusResponse>(res);
}

export async function createDiffReview(payload: {
  title?: string;
  description: string;
  git_diff: string;
  demo_mode?: boolean;
}): Promise<ReviewDetailResponse> {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title || undefined,
      description: payload.description,
      submission_type: "diff",
      git_diff: payload.git_diff,
      demo_mode: payload.demo_mode,
    }),
  });
  return handleJson<ReviewDetailResponse>(res);
}

export async function createFilesReview(payload: {
  title?: string;
  description: string;
  files: Array<{ path: string; content: string; status?: "added" | "modified" }>;
  demo_mode?: boolean;
}): Promise<ReviewDetailResponse> {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title || undefined,
      description: payload.description,
      submission_type: "files",
      files: payload.files,
      demo_mode: payload.demo_mode,
    }),
  });
  return handleJson<ReviewDetailResponse>(res);
}

export async function approvePatch(reviewId: string): Promise<FixSuggestion> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/patch/approve`, {
    method: "POST",
  });
  return handleJson<FixSuggestion>(res);
}

export function getPatchDownloadUrl(reviewId: string): string {
  return `${API_BASE}/reviews/${reviewId}/patch/download`;
}

export async function deleteReviewRecord(reviewId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}`, { method: "DELETE" });
  await handleJson<{ deleted: boolean }>(res);
}

