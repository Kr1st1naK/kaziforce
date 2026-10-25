/** The score badge: the band is always a word, never a colour alone, and never "confidence". */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchScoreBadge, SkillChips, formatKes } from "@/components/MatchCard";
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
