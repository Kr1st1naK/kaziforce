/** The score badge: the band is always a word, never a colour alone, and never "confidence". */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EXCERPT_CHARS, MatchCard, MatchScoreBadge, SkillChips, excerpt, formatKes } from "@/components/MatchCard";
import type { Band } from "@/lib/types";

describe("MatchScoreBadge", () => {
  it.each<[number, Band, string]>([
    [84, "strong", "Strong"],
    [71, "moderate", "Moderate"],
    [57, "weak", "Weak"],
  ])("shows %i as %s", (score, band, label) => {
    const { unmount } = render(<MatchScoreBadge score={score} band={band} />);
    expect(screen.getByText(`Match score ${score}`)).toBeInTheDocument();
    expect(screen.getByText(label)).toBeInTheDocument();
    unmount();
  });

  it("never uses the word confidence", () => {
    const { container } = render(<MatchScoreBadge score={84} band="strong" />);
    expect(container.textContent?.toLowerCase()).not.toContain("confidence");
  });
});

describe("SkillChips", () => {
  it("shows the first few and counts the rest", () => {
    render(<SkillChips skills={["conduit piping", "breaker box repair", "solar wiring", "earthing", "trunking"]} />);
    expect(screen.getByText("conduit piping")).toBeInTheDocument();
    expect(screen.queryByText("earthing")).not.toBeInTheDocument();
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("makes the count a link to the explanation when it is given one", () => {
    render(<SkillChips skills={["a", "b", "c", "d", "e"]} moreHref="/worker/matches/p-1" />);
    const link = screen.getByRole("link", { name: /\+2 more/ });
    expect(link).toHaveAttribute("href", "/worker/matches/p-1");
    expect(link).toHaveTextContent("+2 more");
  });

  it("is plain text when there is nowhere to link to, and shows the same skills either way", () => {
    render(<SkillChips skills={["a", "b", "c", "d", "e"]} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("counts nothing when everything fits", () => {
    render(<SkillChips skills={["conduit piping"]} />);
    expect(screen.queryByText(/more/)).not.toBeInTheDocument();
  });
});

describe("formatKes", () => {
  it("writes an amount with its unit, and says when there is none", () => {
    expect(formatKes(2500)).toBe("KES 2,500 / day");
    expect(formatKes(null)).toBe("Not stated");
  });
});

describe("MatchCard", () => {
  const result = {
    rank: 1, posting_id: "p-7", title: "Rewire an old shop", location: "Nairobi - Kasarani", budget: 3000, availability: "Full-time",
    match_score: 71, band: "moderate",
    matched_skills: ["a", "b", "c", "d", "e"].map((skill_label) => ({ skill_label })),
  } as unknown as import("@/lib/types").MatchResult;

  it("sends both \"+N more\" and \"Why this job?\" to the same explanation", () => {
    render(<MatchCard result={result} href="/worker/matches/p-7" />);
    expect(screen.getByRole("link", { name: /\+2 more/ })).toHaveAttribute("href", "/worker/matches/p-7");
    expect(screen.getByRole("link", { name: "Why this job?" })).toHaveAttribute("href", "/worker/matches/p-7");
    expect(screen.getAllByText(/^[a-c]$/)).toHaveLength(3); // the card still shows the same three skills
  });
});

describe("the job's details on the card (U-11)", () => {
  const base = {
    rank: 1, posting_id: "p-9", title: "Install a new distribution board", location: "Nairobi - Kasarani", budget: 3000,
    availability: "Full-time", match_score: 71, band: "moderate", matched_skills: [],
  };
  const withDescription = (description: string) => ({ ...base, description }) as unknown as import("@/lib/types").MatchResult;

  it("shows a short description under the title and facts", () => {
    render(<MatchCard result={withDescription("A new board for a three-bedroom house in Kasarani. Materials are on site.")} href="/worker/matches/p-9" />);
    expect(screen.getByText(/A new board for a three-bedroom house in Kasarani/)).toBeInTheDocument();
  });

  it("cuts a very long description at a word, so the card takes a few lines and not thousands of characters", () => {
    const long = "work location pay details compensation ".repeat(400); // about 15,600 characters
    const { container } = render(<MatchCard result={withDescription(long)} href="/worker/matches/p-9" />);
    const shown = container.querySelector("[class*=excerpt]")!.textContent!;
    expect(shown.length).toBeLessThanOrEqual(EXCERPT_CHARS + 1);
    expect(shown.endsWith("…")).toBe(true);
    expect(shown).not.toMatch(/ …$/); // cut at a word, no dangling space
  });

  it("is plain text: markup in a description is shown as written and never becomes an element", () => {
    const { container } = render(<MatchCard result={withDescription('<b>Urgent</b> <img src=x onerror="alert(1)"> wiring')} href="/worker/matches/p-9" />);
    expect(container.querySelector("b, img, script")).toBeNull();
    expect(container.textContent).toContain("<b>Urgent</b>");
  });

  it("has no empty paragraph when a posting has no description", () => {
    const { container } = render(<MatchCard result={withDescription("   ")} href="/worker/matches/p-9" />);
    expect(container.querySelector("[class*=excerpt]")).toBeNull();
  });
});

describe("excerpt", () => {
  it("leaves a short text alone, collapses whitespace, and copes with nothing", () => {
    expect(excerpt("  Rewire   a\nshop ")).toBe("Rewire a shop");
    expect(excerpt("")).toBe("");
    expect(excerpt(null)).toBe("");
    expect(excerpt(undefined)).toBe("");
  });

  it("cuts a word-less run of characters at the limit rather than not at all", () => {
    const run = "a".repeat(1000);
    expect(excerpt(run, 100)).toBe(`${"a".repeat(100)}…`);
  });
});
