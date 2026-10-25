/**
 * The plain-language explanation, composed in the interface from what the API
 * already returns: the matched skills with their provenance, the per-criterion
 * scores, and the two profiles. The API stays a data contract; the sentences
 * are presentation.
 *
 * Two lists come out of it, matching the design: what lined up, and what we
 * couldn't check. Nothing is asserted that the data does not support — a
 * criterion the engine could not assess is reported as not checked, never as a
 * failure and never as a zero.
 */

import type { MatchResult, Worker } from "./types";

/** "part of X" for each trade in the vocabulary. Falls back to "a <trade>'s work". */
const TRADE_PHRASE: Record<string, string> = {
  electrician: "electrical work",
  plumber: "plumbing work",
  carpenter: "carpentry",
  bricklayer: "masonry work",
  "vehicle technician": "motor vehicle repair",
  "mobile phone repair technician": "phone repair",
  tailor: "tailoring",
  hairdresser: "hairdressing",
  barber: "barbering",
  "laundry worker": "laundry work",
  cook: "cooking",
};

export function tradePhrase(occupation: string): string {
  return TRADE_PHRASE[occupation.toLowerCase()] ?? `a ${occupation}'s work`;
}

export function formatKes(amount: number): string {
  return `KES ${amount.toLocaleString("en-KE")}`;
}

/** The trade an inferred skill was reached through, from the first node of its path. */
function originOf(skill: MatchResult["matched_skills"][number]): string | null {
  return skill.graph_path.at(-1)?.source.label ?? null;
}

export function whatLinedUp(result: MatchResult, worker: Worker): string[] {
  const lines: string[] = [];
  let inferredAlready = false;

  for (const skill of result.matched_skills) {
    if (skill.source === "listed" || skill.source === "text") {
      lines.push(`You said you do ${skill.skill_label}, and this job mentions it.`);
      continue;
    }
    const occupation = originOf(skill);
    const phrase = occupation ? tradePhrase(occupation) : null;
    if (!phrase) continue;
    // "needs someone to install sockets" for a skill; "needs electrical wiring plans" for knowledge.
    const lead = skill.skill_type === "skill" ? "someone to " : "";
    lines.push(`This job needs ${lead}${skill.skill_label}. That's part of ${phrase}${inferredAlready ? " too" : ""}.`);
    inferredAlready = true;
  }

  const components = result.rule_components;
  if (components?.location === 1 && worker.location) {
    lines.push(`You're both in ${worker.location}.`);
  }
  if (components?.budget_fit === 1 && worker.rate_expectation !== null) {
    lines.push(`Your rate of ${formatKes(worker.rate_expectation)} a day fits their budget.`);
  }
  if (components?.availability === 1 && worker.availability && result.availability) {
    lines.push(`You can work ${worker.availability.toLowerCase()}, and that suits this job.`);
  }
  return lines;
}

/**
 * Criteria the engine could not assess, said in the worker's terms. A criterion is
 * null when the field is missing on the profile or on the posting; the sentence names
 * whichever side is missing.
 */
export function whatWeCouldNotCheck(result: MatchResult, worker: Worker): string[] {
  const components = result.rule_components;
  if (!components) return [];
  const lines: string[] = [];

  if (components.availability === null) {
    lines.push(
      worker.availability === null
        ? "You haven't said when you can work, so we couldn't check that."
        : "This job doesn't say when it's needed, so we couldn't check that.",
    );
  }
  if (components.budget_fit === null) {
    lines.push(
      worker.rate_expectation === null
        ? "You haven't given a daily rate, so we couldn't compare it with their budget."
        : "This job doesn't give a budget, so we couldn't compare it with your rate.",
    );
  }
  if (components.location === null) {
    lines.push(
      worker.location === null
        ? "You haven't said where you work, so we couldn't check the location."
        : "This job doesn't say where it is, so we couldn't check the location.",
    );
  }
  if (components.skill_overlap === null) {
    lines.push("There were no skills to compare on this job.");
  }
  return lines;
}

/** "You described yourself as a fundi wa umeme. We matched that to the trade electrician." */
export function vocabularyNote(result: MatchResult): { term: string; occupation: string } | null {
  const inferred = result.matched_skills.find((skill) => skill.source === "informal_term");
  const path = inferred?.graph_path;
  if (!path || path.length === 0) return null;
  return { term: path[0].source.label, occupation: path[0].target.label };
}

/** The graph trace shown in the technical detail, as one line of text. */
export function graphTrace(result: MatchResult): string | null {
  const skill = result.matched_skills.find((candidate) => candidate.graph_path.length > 0);
  if (!skill) return null;
  const steps = skill.graph_path
    .map((edge) => `--${edge.relation}⟶ ${edge.target.label}`)
    .join(" ");
  return `"${skill.graph_path[0].source.label}" ${steps} --required by⟶ ${result.title}`;
}
