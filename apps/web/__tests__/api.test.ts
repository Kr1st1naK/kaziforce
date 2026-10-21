/** The API client: waiting out the 503 during startup, and mapping an error to its field. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/lib/api";

function response(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => headers[name] ?? null },
    json: async () => body,
  } as unknown as Response;
}

const notReady = () =>
  response(503, { error: { code: "not_ready", message: "the recommendation engine is still loading" } },
    { "Retry-After": "5" });

describe("api", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("retries while the engine is loading, then returns the result", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(notReady())
      .mockResolvedValueOnce(notReady())
      .mockResolvedValueOnce(response(200, { results: [] }));
    vi.stubGlobal("fetch", fetchMock);

    const pending = api.recommend("worker-1", 10);
    await vi.advanceTimersByTimeAsync(11_000);
    await expect(pending).resolves.toEqual({ results: [] });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("gives up once the retry budget is spent", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(notReady()));
    const pending = api.recommend("worker-1", 10).catch((error: ApiError) => error);
    await vi.advanceTimersByTimeAsync(120_000);
    const error = (await pending) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("not_ready");
    expect(error.isNotReady).toBe(true);
  });

  it("does not retry a health check, so a status poll returns at once", async () => {
    const fetchMock = vi.fn().mockResolvedValue(notReady());
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("keeps the field a 400 names, so the form can point at it", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(400, {
          error: { code: "invalid_request", message: "worker.availability must be one of …", field: "worker.availability" },
        }),
      ),
    );
    const error = (await api
      .createWorker({ biography: "x", skills: [], location: null, availability: null, rate_expectation: null })
      .catch((caught: ApiError) => caught)) as ApiError;
    expect(error.status).toBe(400);
    expect(error.field).toBe("worker.availability");
  });

  it("reports an unreachable API as a network error, not a crash", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = (await api.job("abc").catch((caught: ApiError) => caught)) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.message).toContain("Cannot reach the API");
  });
});
