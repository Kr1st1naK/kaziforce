/**
 * A null score must never read as 0.
 *
 * The API returns null for a component a configuration does not use, and for a
 * criterion whose field is missing on either side. Rendering that as 0% would
 * claim the system assessed something and found nothing, which is a different
 * and wrong statement. These tests render null and 0 side by side and require
 * them to differ, in the text and in the bar.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NOT_ASSESSED, ScoreBar, ScoreValue, formatScore } from "@/components/ScoreValue";

describe("ScoreValue", () => {
  it("renders null as 'Not assessed' and 0 as a real zero score", () => {
    const { container } = render(
      <>
        <ScoreValue value={null} />
        <ScoreValue value={0} />
      </>,
    );
    expect(container.textContent).toBe(`${NOT_ASSESSED}0%`);
    expect(screen.getByText(NOT_ASSESSED)).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(container.textContent).not.toBe("0%0%");
  });

  it("explains why a value is absent", () => {
    render(<ScoreValue value={null} />);
    expect(screen.getByText(NOT_ASSESSED)).toHaveAttribute(
      "title",
      expect.stringContaining("missing from the profile or the posting"),
    );
  });

  it("rounds a score to whole percentages", () => {
    expect(formatScore(0)).toBe("0%");
    expect(formatScore(0.8)).toBe("80%");
    expect(formatScore(0.6951)).toBe("70%");
    expect(formatScore(1)).toBe("100%");
  });
});

describe("ScoreBar", () => {
  it("draws no fill for an absent score, and a zero-width fill for a real zero", () => {
    const { container: absent } = render(<ScoreBar label="Rule-based score" value={null} />);
    const { container: zero } = render(<ScoreBar label="Rule-based score" value={0} />);

    const absentTrack = absent.querySelector('[role="img"]') as HTMLElement;
    const zeroTrack = zero.querySelector('[role="img"]') as HTMLElement;

    expect(absentTrack.getAttribute("aria-label")).toBe(`Rule-based score: ${NOT_ASSESSED}`);
    expect(zeroTrack.getAttribute("aria-label")).toBe("Rule-based score: 0%");
    expect(absentTrack.className).not.toBe(zeroTrack.className);
    expect(absentTrack.children).toHaveLength(0);
    expect(zeroTrack.children).toHaveLength(1);
  });

  it("clamps a fill to the width of the track", () => {
    const { container } = render(<ScoreBar label="Semantic score" value={1.4} />);
    expect((container.querySelector('[role="img"] > div') as HTMLElement).style.width).toBe("100%");
  });
});
