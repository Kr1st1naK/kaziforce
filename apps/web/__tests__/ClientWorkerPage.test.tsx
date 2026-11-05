/**
 * A client opens a worker they found on a job's confirmation screen: the name, the trade, the
 * facts, the worker's own words, and a phone number to ring. Nothing that ranks, and a plain
 * answer when the worker is gone.
 */

import { act, render, screen, type RenderResult } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/client/workers/[workerId]/page";
import { ApiError } from "@/lib/api";
import type { ClientWorkerView } from "@/lib/types";

let query = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/client/workers/x",
  useSearchParams: () => new URLSearchParams(query),
}));

const clientWorker = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { clientWorker: (id: string) => clientWorker(id) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));
vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

const WORKER: ClientWorkerView = {
  public_id: "11111111-2222-4333-8444-555555555555",
  first_name: "Amina",
  last_name: "Wanjiru",
  trade: "plumber",
  skills: ["fundi bomba", "replace faucets"],
  biography: "Fundi bomba mwenye uzoefu wa miaka sita.",
  location: "Nairobi - Kasarani",
  availability: "Full-time",
  rate_expectation: 2400,
  contact: { phone_e164: "+254712345678", phone_local: "712345678" },
};

const POSTING = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";

// One promise for every render: `use()` keys on its identity, and a fresh one each time never settles.
const PARAMS = Promise.resolve({ workerId: WORKER.public_id });

// Rendered inside act, so the first suspension on `use(params)` is flushed before anything is asserted.
async function show(): Promise<RenderResult> {
  let rendered!: RenderResult;
  await act(async () => {
    rendered = render(<Page params={PARAMS} />);
  });
  return rendered;
}

beforeEach(() => {
  vi.clearAllMocks();
  query = "";
  clientWorker.mockResolvedValue(WORKER);
});

describe("a worker's profile for a client", () => {
  it("asks the API for the worker in the address", async () => {
    await show();
    await screen.findByRole("heading", { name: "Amina Wanjiru" });
    expect(clientWorker).toHaveBeenCalledWith(WORKER.public_id);
  });

  it("says it is loading until the worker arrives", async () => {
    clientWorker.mockReturnValue(new Promise(() => {}));
    await show();
    expect(await screen.findByRole("status")).toHaveTextContent("Loading");
  });

  it("shows the name, the trade, the worker's own words and the facts", async () => {
    await show();
    expect(await screen.findByRole("heading", { name: "Amina Wanjiru" })).toBeVisible();
    expect(screen.getByText("plumber")).toBeVisible();
    expect(screen.getByText("“fundi bomba, replace faucets”")).toBeVisible();
    expect(screen.getByText("Fundi bomba mwenye uzoefu wa miaka sita.")).toBeVisible();
    expect(screen.getByText("Nairobi - Kasarani")).toBeVisible();
    expect(screen.getByText("Full-time")).toBeVisible();
    expect(screen.getByText(/2,400/)).toBeVisible();
  });

  it("offers the phone number as a tap-to-call link, and shows it formatted", async () => {
    await show();
    const call = await screen.findByRole("link", { name: /Call Amina Wanjiru/ });
    expect(call).toHaveAttribute("href", "tel:+254712345678");
    expect(call).toHaveTextContent("+254 712 345 678");
  });

  it("says what is not stated instead of leaving a gap", async () => {
    clientWorker.mockResolvedValue({ ...WORKER, location: null, availability: null, rate_expectation: null, trade: null });
    await show();
    await screen.findByRole("heading", { name: "Amina Wanjiru" });
    expect(screen.getAllByText("Not stated")).toHaveLength(3);
  });

  it("links back to the job posting the client came from", async () => {
    query = `posting=${POSTING}`;
    await show();
    expect(await screen.findByRole("link", { name: /Back to your job posting/ })).toHaveAttribute(
      "href",
      `/client/postings/${POSTING}`,
    );
  });

  it("falls back to the postings list when there is no posting, or an odd one", async () => {
    for (const odd of ["", "posting=../../evil", "posting=javascript:alert(1)"]) {
      query = odd;
      const { unmount } = await show();
      expect(await screen.findByRole("link", { name: /Back to my postings/ })).toHaveAttribute("href", "/client/postings");
      unmount();
    }
  });

  it("carries no score, rank or match wording", async () => {
    const { container } = await show();
    await screen.findByRole("heading", { name: "Amina Wanjiru" });
    expect(container.textContent).not.toMatch(/score|rank|best match|top match|#\d/i);
  });
});

describe("when the profile cannot be shown", () => {
  it("says it is not available when the worker has withdrawn or never existed, and shows no profile", async () => {
    clientWorker.mockRejectedValue(new ApiError(404, "not_found", "This worker's profile is not available."));
    await show();
    expect(await screen.findByRole("alert")).toHaveTextContent("not available");
    expect(screen.queryByRole("heading", { name: "Amina Wanjiru" })).toBeNull();
    expect(screen.queryByRole("link", { name: /Call/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Back to my postings/ })).toBeVisible();
  });

  it("asks the client to wait when they have been viewing profiles too quickly", async () => {
    clientWorker.mockRejectedValue(new ApiError(429, "rate_limited", "slow down"));
    await show();
    expect(await screen.findByRole("alert")).toHaveTextContent("Wait a minute");
  });

  it("reports any other failure in the API's own words", async () => {
    clientWorker.mockRejectedValue(new ApiError(500, "internal_error", "internal server error"));
    await show();
    expect(await screen.findByRole("alert")).toHaveTextContent("internal server error");
  });
});
