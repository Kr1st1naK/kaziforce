/** The score badge: the band is always a word, never a colour alone, and never "confidence". */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchCard, MatchScoreBadge, SkillChips, formatKes } from "@/components/MatchCard";
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
