/**
 * A criterion the engine could not assess must never read as 0.
 *
 * "Not assessed" and "0" are different claims: one says we had nothing to
 * compare, the other says we compared and found nothing in common. These tests
 * render both side by side and require them to differ.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CriterionValue, NOT_ASSESSED, ProvenanceBadge } from "@/components/Explanation";
import type { GraphEdge, MatchedSkill } from "@/lib/types";

const TERM = { id: "term:fundi umeme", label: "fundi wa umeme", type: "InformalTerm" } as const;
const OCCUPATION = { id: "esco:electrician", label: "electrician", type: "Occupation" } as const;
const SKILL = { id: "esco:sockets", label: "install electricity sockets", type: "Skill" } as const;

const VIA_TERM: GraphEdge[] = [
  { source: TERM, relation: "MAPS_TO", target: OCCUPATION },
  { source: OCCUPATION, relation: "HAS_ESSENTIAL_SKILL", target: SKILL },
];
const VIA_OCCUPATION: GraphEdge[] = [{ source: OCCUPATION, relation: "HAS_ESSENTIAL_SKILL", target: SKILL }];

function skill(partial: Partial<MatchedSkill>): MatchedSkill {
  return {
    skill: "esco:sockets",
    skill_label: "install electricity sockets",
    source: "listed",
    skill_type: "skill",
    graph_path: [],
    ...partial,
  };
}

describe("CriterionValue", () => {
  it("renders an unassessed criterion as words, and a zero as a zero", () => {
    const { container } = render(
      <>
        <CriterionValue value={null} />
        <CriterionValue value={0} />
      </>,
    );
    expect(container.textContent).toBe(`${NOT_ASSESSED}0`);
    expect(screen.getByText(NOT_ASSESSED)).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(container.textContent).not.toBe("00");
  });

  it("sets 'Not assessed' apart from a real score, not by colour alone", () => {
    const { container: absent } = render(<CriterionValue value={null} />);
    const { container: zero } = render(<CriterionValue value={0} />);
    expect(absent.firstElementChild?.className).not.toBe(zero.firstElementChild?.className);
    expect(absent.firstElementChild).toHaveAttribute("title", expect.stringContaining("missing"));
  });

  it("shows a score out of 100", () => {
    const { container } = render(<CriterionValue value={0.85} />);
    expect(container.textContent).toBe("85");
  });
});

describe("ProvenanceBadge", () => {
  it("uses the four agreed labels", () => {
    const cases: [MatchedSkill, string][] = [
      [skill({ source: "listed" }), "Listed by you"],
      [skill({ source: "text", skill_label: "solar installation" }), "Your own words"],
      [skill({ source: "informal_term", graph_path: VIA_TERM }), "Inferred via fundi wa umeme"],
      [skill({ source: "occupation_label", graph_path: VIA_OCCUPATION }), "Inferred via occupation: electrician"],
    ];
    for (const [matched, label] of cases) {
      const { unmount } = render(<ProvenanceBadge skill={matched} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("never says 'confidence'", () => {
    const { container } = render(<ProvenanceBadge skill={skill({ source: "informal_term", graph_path: VIA_TERM })} />);
    expect(container.textContent?.toLowerCase()).not.toContain("confidence");
  });

  it("falls back to a neutral label for a source it does not know", () => {
    render(<ProvenanceBadge skill={skill({ source: "something_new" as MatchedSkill["source"] })} />);
    expect(screen.getByText("Matched")).toBeInTheDocument();
  });
});
