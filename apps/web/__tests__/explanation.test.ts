/**
 * The plain-language explanation, composed from API data.
 *
 * The wording has to be honest: a criterion the engine could not assess must be
 * reported as unchecked, never as a failure, and the trade phrase must come
 * from the occupation the skill was actually reached through.
 */

import { describe, expect, it } from "vitest";
import { graphTrace, tradePhrase, vocabularyNote, whatLinedUp, whatWeCouldNotCheck } from "@/lib/explanation";
import type { GraphEdge, MatchResult, MatchedSkill, RuleComponents, Worker } from "@/lib/types";

const TERM = { id: "term:fundi umeme", label: "fundi wa umeme", type: "InformalTerm" } as const;
const OCCUPATION = { id: "esco:electrician", label: "electrician", type: "Occupation" } as const;
const SKILL = { id: "esco:sockets", label: "install electricity sockets", type: "Skill" } as const;

const VIA_TERM: GraphEdge[] = [
  { source: TERM, relation: "MAPS_TO", target: OCCUPATION },
  { source: OCCUPATION, relation: "HAS_ESSENTIAL_SKILL", target: SKILL },
];
const VIA_OCCUPATION: GraphEdge[] = [{ source: OCCUPATION, relation: "HAS_ESSENTIAL_SKILL", target: SKILL }];

function skill(partial: Partial<MatchedSkill> = {}): MatchedSkill {
  return {
    skill: "esco:sockets",
    skill_label: "install electricity sockets",
    source: "occupation_label",
    skill_type: "skill",
    graph_path: VIA_OCCUPATION,
    ...partial,
  };
}

function components(partial: Partial<RuleComponents> = {}): RuleComponents {
  return { skill_overlap: 1, location: 1, budget_fit: 1, availability: 1, ...partial };
}

function result(partial: Partial<MatchResult> = {}): MatchResult {
  return {
    rank: 1,
    posting_id: "job-1",
    title: "Three-Phase Distribution Board Installation & Circuit Wiring",
    description: "",
    location: "Nairobi - Kasarani",
    availability: "Full-time",
    budget: 2500,
    scores: { composite: 0.84, rule: 0.82, semantic: 0.74 },
    match_score: 84,
    band: "strong",
    rule_components: components(),
    matched_skills: [skill()],
    ...partial,
  };
}

function worker(partial: Partial<Worker> = {}): Worker {
  return {
    worker_id: "w-1",
    biography: "Mimi ni fundi wa umeme.",
    skills: ["fundi wa umeme"],
    location: "Nairobi - Kasarani",
    availability: "Full-time",
    rate_expectation: 2500,
    ...partial,
  };
}

describe("tradePhrase", () => {
  it("uses the agreed phrase for every trade in the vocabulary", () => {
    expect(tradePhrase("electrician")).toBe("electrical work");
    expect(tradePhrase("bricklayer")).toBe("masonry work");
    expect(tradePhrase("mobile phone repair technician")).toBe("phone repair");
    expect(tradePhrase("cook")).toBe("cooking");
  });

  it("falls back to the occupation itself for a trade it does not know", () => {
    expect(tradePhrase("welder")).toBe("a welder's work");
  });
});

describe("whatLinedUp", () => {
  it("says a job needs someone to do a skill, but simply needs knowledge", () => {
    const lines = whatLinedUp(
      result({
        matched_skills: [
          skill(),
          skill({ skill: "esco:plans", skill_label: "electrical wiring plans", skill_type: "knowledge" }),
        ],
      }),
      worker(),
    );
    expect(lines[0]).toBe("This job needs someone to install electricity sockets. That's part of electrical work.");
    expect(lines[1]).toBe("This job needs electrical wiring plans. That's part of electrical work too.");
  });

  it("credits a skill the worker listed to the worker", () => {
    const lines = whatLinedUp(
      result({ matched_skills: [skill({ source: "listed", skill_label: "breaker box repair", graph_path: [] })] }),
      worker(),
    );
    expect(lines).toContain("You said you do breaker box repair, and this job mentions it.");
  });

  it("names the informal term a skill was inferred through", () => {
    const lines = whatLinedUp(
      result({ matched_skills: [skill({ source: "informal_term", graph_path: VIA_TERM })] }),
      worker(),
    );
    expect(lines[0]).toContain("That's part of electrical work");
  });

  it("mentions location and rate only when they actually matched", () => {
    const matched = whatLinedUp(result(), worker());
    expect(matched).toContain("You're both in Nairobi - Kasarani.");
    expect(matched).toContain("Your rate of KES 2,500 a day fits their budget.");

    const partial = whatLinedUp(result({ rule_components: components({ location: 0, budget_fit: 0.5 }) }), worker());
    expect(partial.some((line) => line.includes("You're both in"))).toBe(false);
    expect(partial.some((line) => line.includes("fits their budget"))).toBe(false);
  });
});

describe("whatWeCouldNotCheck", () => {
  it("says which side is missing, and never calls it a failure", () => {
    const lines = whatWeCouldNotCheck(
      result({ rule_components: components({ availability: null }) }),
      worker({ availability: null }),
    );
    expect(lines).toEqual(["You haven't said when you can work, so we couldn't check that."]);
    expect(lines.join(" ")).not.toMatch(/0|fail|no match/i);
  });

  it("blames the posting when it is the posting that is silent", () => {
    const lines = whatWeCouldNotCheck(
      result({ rule_components: components({ budget_fit: null }) }),
      worker({ rate_expectation: 2500 }),
    );
    expect(lines).toEqual(["This job doesn't give a budget, so we couldn't compare it with your rate."]);
  });

  it("is empty when everything was assessed", () => {
    expect(whatWeCouldNotCheck(result(), worker())).toEqual([]);
  });

  it("says nothing at all when there is no rule component", () => {
    expect(whatWeCouldNotCheck(result({ rule_components: null }), worker())).toEqual([]);
  });
});

describe("vocabularyNote and graphTrace", () => {
  it("reports the term and the trade it was matched to", () => {
    const note = vocabularyNote(result({ matched_skills: [skill({ source: "informal_term", graph_path: VIA_TERM })] }));
    expect(note).toEqual({ term: "fundi wa umeme", occupation: "electrician" });
  });

  it("has no note when nothing was inferred from an informal term", () => {
    expect(vocabularyNote(result({ matched_skills: [skill({ source: "listed", graph_path: [] })] }))).toBeNull();
  });

  it("writes the path as one readable line", () => {
    const trace = graphTrace(result({ matched_skills: [skill({ source: "informal_term", graph_path: VIA_TERM })] }));
    expect(trace).toContain('"fundi wa umeme"');
    expect(trace).toContain("MAPS_TO");
    expect(trace).toContain("install electricity sockets");
    expect(trace).toContain("required by");
  });
});
