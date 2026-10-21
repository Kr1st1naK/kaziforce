/** Each of the four `source` values reads differently, and an unknown one does not break the page. */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchedSkillList, SkillBadge, originLabel } from "@/components/SkillBadge";
import type { GraphEdge, MatchedSkill } from "@/lib/types";

const TERM = { id: "term:fundi umeme", label: "fundi wa umeme", type: "InformalTerm" } as const;
const OCCUPATION = { id: "esco:electrician", label: "electrician", type: "Occupation" } as const;
const SKILL = { id: "esco:sockets", label: "install electricity sockets", type: "Skill" } as const;

const viaTerm: GraphEdge[] = [
  { source: TERM, relation: "MAPS_TO", target: OCCUPATION },
  { source: OCCUPATION, relation: "HAS_ESSENTIAL_SKILL", target: SKILL },
];

function skill(partial: Partial<MatchedSkill>): MatchedSkill {
  return {
    skill: "esco:sockets",
    skill_label: "install electricity sockets",
    source: "listed",
    graph_path: [],
    ...partial,
  };
}

describe("SkillBadge", () => {
  it("distinguishes a skill you listed from one inferred from your wording", () => {
    const { container: listed } = render(<SkillBadge skill={skill({ source: "listed" })} />);
    const { container: inferred } = render(
      <SkillBadge skill={skill({ source: "informal_term", graph_path: viaTerm })} />,
    );
    expect(listed.textContent).toContain("listed by you");
    expect(inferred.textContent).toContain("inferred via fundi wa umeme");
    expect(listed.textContent).not.toBe(inferred.textContent);
  });

  it("names the occupation when the skill came from an occupation in your text", () => {
    render(
      <SkillBadge
        skill={skill({ source: "occupation_label", graph_path: [viaTerm[1]] })}
      />,
    );
    expect(screen.getByText("inferred via occupation electrician")).toBeInTheDocument();
  });

  it("calls the client's own words what they are", () => {
    render(<SkillBadge skill={skill({ source: "text", skill_label: "rewiring sockets" })} />);
    expect(screen.getByText("your own words")).toBeInTheDocument();
  });

  it("falls back to a neutral badge for a source it does not know", () => {
    render(<SkillBadge skill={skill({ source: "something_new" as MatchedSkill["source"] })} />);
    expect(screen.getByText("matched")).toBeInTheDocument();
  });

  it("takes the origin from the first node of the path", () => {
    expect(originLabel(skill({ source: "informal_term", graph_path: viaTerm }))).toBe("fundi wa umeme");
    expect(originLabel(skill({}))).toBeNull();
  });
});

describe("MatchedSkillList", () => {
  it("shows a limited number and counts the rest", () => {
    const skills = ["a", "b", "c", "d", "e"].map((id) => skill({ skill: id, skill_label: `skill ${id}` }));
    render(<MatchedSkillList skills={skills} limit={3} />);
    expect(screen.getByText("skill a")).toBeInTheDocument();
    expect(screen.queryByText("skill d")).not.toBeInTheDocument();
    expect(screen.getByText("and 2 more")).toBeInTheDocument();
  });
});
