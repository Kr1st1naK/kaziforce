/**
 * "Why this job?" shows the job itself: the full description, as plain text, under "About this job" (usability
 * finding U-11: "have descriptions about the job"). The explanation below it is untouched.
 */

import { act, render, screen, type RenderResult } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/worker/matches/[postingId]/page";
import type { MatchResult } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/worker/matches/p-1",
}));

const myMatches = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { myMatches: (k: number) => myMatches(k) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));
vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

const PARAMS = Promise.resolve({ postingId: "p-1" });

function result(description: string): MatchResult {
  return {
    rank: 1, posting_id: "p-1", title: "Install a new distribution board", description, location: "Nairobi - Kasarani",
    availability: "Full-time", budget: 3000, scores: { composite: 0.71, rule: 0.7, semantic: 0.72 }, match_score: 71,
    band: "moderate", rule_components: null, matched_skills: [],
    explanation: { rank: 1, posting_id: "p-1", reasons: [{ kind: "criterion", text: "You're both in Nairobi - Kasarani." }], not_assessed: [], covered: true },
  } as unknown as MatchResult;
}

async function show(description: string): Promise<RenderResult> {
  myMatches.mockResolvedValue({ results: [result(description)] });
  let rendered!: RenderResult;
  await act(async () => {
    rendered = render(<Page params={PARAMS} />);
  });
  return rendered;
}

beforeEach(() => vi.clearAllMocks());

describe("About this job", () => {
  it("shows the whole description under its own heading, above the explanation", async () => {
    const text = "A new board for a three-bedroom house.\nMaterials are on site. Access from 8 am.";
    await show(text);

    const heading = await screen.findByRole("heading", { name: "About this job" });
    const region = screen.getByRole("region", { name: "Full job description" });
    expect(region).toHaveTextContent("A new board for a three-bedroom house.");
    expect(region.textContent).toBe(text);
    expect(heading.compareDocumentPosition(screen.getByText("You're both in Nairobi - Kasarani."))).toBeTruthy();
    expect(heading.compareDocumentPosition(region) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows a very long description in full, in a box that can be scrolled by keyboard", async () => {
    const long = "work location pay details compensation ".repeat(400);
    await show(long);

    const region = await screen.findByRole("region", { name: "Full job description" });
    expect(region.textContent).toBe(long);
    expect(region).toHaveAttribute("tabindex", "0");
  });

  it("is plain text: markup is shown as written and never becomes an element", async () => {
    const { container } = await show('<script>alert(1)</script><b>Urgent</b>');

    const region = await screen.findByRole("region", { name: "Full job description" });
    expect(region.textContent).toBe("<script>alert(1)</script><b>Urgent</b>");
    expect(container.querySelector("script, b")).toBeNull();
  });

  it("leaves out the section when a posting has no description, and keeps the explanation", async () => {
    await show("   ");

    expect(await screen.findByText("You're both in Nairobi - Kasarani.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "About this job" })).not.toBeInTheDocument();
  });
});
