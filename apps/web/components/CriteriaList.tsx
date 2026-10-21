/**
 * The four rule criteria, always all four, with the absent ones named as such
 * and the reason given (docs/scoring-policy.md §1: an absent criterion is
 * dropped and the remaining weights are renormalised, so it neither adds nor
 * subtracts score).
 */

import { RULE_CRITERIA, type MatchResult, type RuleCriterion } from "@/lib/types";
import { NOT_ASSESSED, ScoreValue } from "./ScoreValue";
import styles from "./CriteriaList.module.css";

const CRITERION_LABEL: Record<RuleCriterion, string> = {
  skill_overlap: "Skills the job asks for",
  location: "Location",
  budget_fit: "Budget against your rate",
  availability: "Availability",
};

function reason(criterion: RuleCriterion, result: MatchResult): string {
  const missing: string[] = [];
  if (criterion === "location" && result.location === null) missing.push("this job gives no location");
  if (criterion === "budget_fit" && result.budget === null) missing.push("this job gives no budget");
  if (criterion === "availability" && result.availability === null) missing.push("this job gives no availability");
  const own = {
    location: "you gave no location",
    budget_fit: "you gave no rate",
    availability: "you gave no availability",
    skill_overlap: "no skills to compare",
  }[criterion];
  missing.push(own);
  return `${NOT_ASSESSED}: ${missing.join(", or ")}. It does not count for or against this match.`;
}

export function CriteriaList({ result }: { result: MatchResult }) {
  const components = result.rule_components;
  if (components === null) {
    return <p className="note">This configuration has no rule-based component, so there is nothing to break down.</p>;
  }
  return (
    <dl className={styles.list}>
      {RULE_CRITERIA.map((criterion) => {
        const value = components[criterion];
        return (
          <div key={criterion} className={styles.item}>
            <dt className={styles.term}>{CRITERION_LABEL[criterion]}</dt>
            <dd className={styles.definition}>
              <ScoreValue value={value} />
              {value === null && <span className={styles.reason}>{reason(criterion, result)}</span>}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
