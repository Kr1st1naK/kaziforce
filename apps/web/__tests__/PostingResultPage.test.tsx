/**
 * The result of posting a job says what is true about how the posting was read, whether or not the client
 * listed skills. With none, the trade is read from the description and skills could not be compared; the old
 * sentence ("We match on the skills you listed above") would have been untrue.
 */

import { act, render, screen, type RenderResult } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/client/postings/[postingId]/page";
import type { JobInterpretation } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/client/postings/p-1",
}));

const job = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { job: (id: string) => job(id) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));
vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

const PLUMBER = { id: "occ:plumber", label: "plumber" };
const NAMED = { describes_as: "fundi bomba", location: "Nairobi - Kasarani", availability: "Full-time" as const, rate_expectation: 2400, public_id: "11111111-2222-4333-8444-555555555555", name: "Amina Wanjiru" };
const ANONYMOUS = { describes_as: "fundi bomba, install pipes", location: "Meru", availability: "Weekends" as const, rate_expectation: 1800 };
const PARAMS = Promise.resolve({ postingId: "p-1" });

function posting(over: Partial<JobInterpretation["interpretation"]>): JobInterpretation {
  return {
    posting_id: "p-1",
    job: { posting_id: "p-1", title: "Fix a leaking tap", description: "I need a plumber to fix a leaking tap", required_skills: [], location: "Nairobi - Kasarani", availability: null, budget: 2500 },
    interpretation: { terms: [], occupations: [PLUMBER], unmapped: [], stated_skills: [], worker_pool: [{ occupation: PLUMBER, workers: 15, sample: [] }], ...over },
    candidate_jobs: 294,
  };
}

async function show(): Promise<RenderResult> {
  let rendered!: RenderResult;
  await act(async () => {
    rendered = render(<Page params={PARAMS} />);
  });
  return rendered;
}

beforeEach(() => vi.clearAllMocks());

describe("a posting with no skills listed", () => {
  it("says the trade was read from the description and that skills could not be compared", async () => {
    job.mockResolvedValue(posting({}));
    await show();

    expect(await screen.findByText(/We matched this to the trade:/)).toHaveTextContent("plumber");
    expect(screen.getByText(/You didn't list any skills, so we couldn't compare skills/)).toBeInTheDocument();
    expect(screen.getByText(/We read the trade from your description/)).toBeInTheDocument();
    expect(screen.queryByText(/We match on the skills you listed above/)).not.toBeInTheDocument();
  });

  it("still says so when no trade was found", async () => {
    job.mockResolvedValue(posting({ occupations: [], worker_pool: [] }));
    await show();

    expect(await screen.findByText(/We couldn't match this to a trade we know/)).toBeInTheDocument();
    expect(screen.getByText(/couldn't compare skills/)).toBeInTheDocument();
  });
});

describe("a posting with skills listed", () => {
  it("keeps the sentence that matching uses the listed skills, and does not claim none were listed", async () => {
    job.mockResolvedValue(
      posting({ stated_skills: [{ skill: "s:1", skill_label: "replace faucets", source: "listed" }] }),
    );
    await show();

    expect(await screen.findByText(/We match on the skills you listed above, and nothing else/)).toBeInTheDocument();
    expect(screen.getByText("replace faucets")).toBeInTheDocument();
    expect(screen.queryByText(/You didn't list any skills/)).not.toBeInTheDocument();
  });
});

describe("Workers in this trade", () => {
  const shown = (sample: unknown[]) => posting({ worker_pool: [{ occupation: PLUMBER, workers: 18, sample: sample as never }] });

  it("says which workers can be opened and which cannot, under the heading", async () => {
    job.mockResolvedValue(shown([NAMED, ANONYMOUS]));
    await show();

    const heading = await screen.findByRole("heading", { name: "Workers in this trade" });
    const note = screen.getByText("Workers who have agreed to be shown can be opened to see contact details. The others cannot.");
    expect(heading.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("makes a worker who agreed an openable card, and leaves the others plain, in the order given", async () => {
    job.mockResolvedValue(shown([ANONYMOUS, NAMED]));
    await show();

    const cards = await screen.findAllByRole("article");
    expect(cards).toHaveLength(2);
    expect(cards[0].textContent).toContain("install pipes"); // the order the API returned
    expect(cards[0].querySelector("a")).toBeNull();
    expect(cards[1].querySelector("a")).toHaveAccessibleName("Amina Wanjiru");
    expect(screen.getAllByRole("link", { name: "Amina Wanjiru" })).toHaveLength(1);
  });
});
