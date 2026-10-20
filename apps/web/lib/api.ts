/**
 * Typed client for the KaziForce API (docs/api.md).
 *
 * The engine takes about half a minute to load after the server starts and
 * answers 503 `not_ready` until then, so every request retries a 503 for up to
 * RETRY_BUDGET_MS, waiting the interval the server asks for. Anything else is
 * raised as an ApiError carrying the server's code, message and field.
 */

import type {
  ApiErrorBody,
  ApiErrorCode,
  CreatedWorker,
  Health,
  JobInput,
  JobInterpretation,
  Recommendation,
  WorkerInput,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000";
export const RETRY_BUDGET_MS = 90_000;
const DEFAULT_RETRY_AFTER_MS = 5_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly field?: string;

  constructor(status: number, code: ApiErrorCode, message: string, field?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }

  /** True while the engine is still loading, so the caller can keep waiting. */
  get isNotReady(): boolean {
    return this.code === "not_ready";
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function retryAfterMs(response: Response): number {
  const header = Number(response.headers.get("Retry-After"));
  return Number.isFinite(header) && header > 0 ? header * 1000 : DEFAULT_RETRY_AFTER_MS;
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    /* a response that is not JSON falls back to the status line below */
  }
  const error = body?.error;
  return new ApiError(
    response.status,
    error?.code ?? "internal_error",
    error?.message ?? `the server returned ${response.status}`,
    error?.field,
  );
}

type RequestOptions = { method?: "GET" | "POST"; body?: unknown; retryWhileLoading?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, retryWhileLoading = true } = options;
  const deadline = Date.now() + RETRY_BUDGET_MS;

  for (;;) {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, "network_error", `Cannot reach the API at ${API_BASE}. Is it running?`);
    }

    if (response.ok) {
      return (await response.json()) as T;
    }
    const error = await toApiError(response);
    if (error.isNotReady && retryWhileLoading && Date.now() < deadline) {
      await sleep(Math.min(retryAfterMs(response), Math.max(0, deadline - Date.now())));
      continue;
    }
    throw error;
  }
}

export const api = {
  /** Readiness; never retried, so a status poll returns at once. */
  health: () => request<Health>("/health", { retryWhileLoading: false }),

  createWorker: (worker: WorkerInput) =>
    request<CreatedWorker>("/workers", { method: "POST", body: worker }),

  createJob: (job: JobInput) => request<JobInterpretation>("/jobs", { method: "POST", body: job }),

  job: (postingId: string) => request<JobInterpretation>(`/jobs/${encodeURIComponent(postingId)}`),

  recommend: (workerId: string, k: number) =>
    request<Recommendation>("/recommend", { method: "POST", body: { worker_id: workerId, k } }),
};
