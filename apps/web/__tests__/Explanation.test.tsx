/**
 * The explanation screen renders what the API generated, and composes nothing.
 *
 * These tests feed it text no sentence-builder would ever produce. If any of it
 * reaches the screen unchanged, the interface is rendering rather than rewriting,
 * which is the property that keeps the backend generator the single source of the
 * wording (FR-09).
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PlainExplanation } from "@/components/Explanation";
import type { Explanation, Reason } from "@/lib/types";

function reason(partial: Partial<Reason> = {}): Reason {
  return {
    kind: "graph_skill",
    text: "This job needs someone to install electricity sockets. That's part of electrical work.",
    skill: "esco:sockets",
    skill_label: "install electricity sockets",
    source: "informal_term",
    occupation: "electrician",
    term: "fundi wa umeme",
    ...partial,
  };
}

function explanation(partial: Partial<Explanation> = {}): Explanation {
  return {
    worker_id: "w-1",
    posting_id: "j-1",
    rank: 1,
    scores: { composite: 0.84, rule: 0.82, semantic: 0.74 },
    reasons: [reason()],
    not_assessed: [],
    covered: true,
    ...partial,
  };
}

describe("PlainExplanation", () => {
  it("renders the API's sentences exactly, without rewriting them", () => {
    const sentences = ["A sentence only the backend would write.", "And a second one."];
    render(<PlainExplanation explanation={explanation({ reasons: sentences.map((text) => reason({ text })) })} />);
    for (const sentence of sentences) expect(screen.getByText(sentence)).toBeInTheDocument();
  });

  it("shows what could not be checked, as its own section and never as a failure", () => {
    const { container } = render(
      <PlainExplanation
        explanation={explanation({
          not_assessed: ["This job doesn't give a budget, so we couldn't compare it with your rate."],
        })}
      />,
    );
    expect(screen.getByRole("heading", { name: "What we couldn't check" })).toBeInTheDocument();
    expect(
      screen.getByText("This job doesn't give a budget, so we couldn't compare it with your rate."),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\b0\b|failed|no match/i);
  });

  it("hides that section when everything was assessed", () => {
    render(<PlainExplanation explanation={explanation()} />);
    expect(screen.queryByRole("heading", { name: "What we couldn't check" })).not.toBeInTheDocument();
  });

  it("names the informal term and the trade it reached", () => {
    render(<PlainExplanation explanation={explanation()} />);
    expect(screen.getByText(/You described yourself as a/)).toBeInTheDocument();
    expect(screen.getByText("fundi wa umeme")).toBeInTheDocument();
    expect(screen.getByText("electrician")).toBeInTheDocument();
  });

  it("has no vocabulary note when nothing came through an informal term", () => {
    render(
      <PlainExplanation
        explanation={explanation({
          reasons: [reason({ kind: "literal_skill", source: "listed", term: undefined, occupation: undefined })],
        })}
      />,
    );
    expect(screen.queryByText(/You described yourself as a/)).not.toBeInTheDocument();
  });

  it("says so plainly when there was nothing specific", () => {
    render(<PlainExplanation explanation={explanation({ reasons: [], covered: false })} />);
    expect(screen.getByText(/Nothing specific lined up/)).toBeInTheDocument();
  });

  it("shows no score, no component and no raw graph path", () => {
    const { container } = render(
      <PlainExplanation explanation={explanation({ reasons: [reason({ score: 1, criterion: "location" })] })} />,
    );
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/Rule-based score|Semantic score|Criteria|MAPS_TO|HAS_ESSENTIAL_SKILL/);
    expect(text.toLowerCase()).not.toContain("confidence");
  });
});
