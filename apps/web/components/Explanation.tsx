"use client";

/**
 * The explanation screen's two halves: the plain-language account, and the
 * technical detail behind it.
 *
 * A criterion the engine could not assess reads "Not assessed" in muted
 * italics, never 0 and never an empty bar — the number would claim the engine
 * looked and found nothing.
 */

import { useState } from "react";
import {
  graphTrace,
  tradePhrase,
  vocabularyNote,
  whatLinedUp,
  whatWeCouldNotCheck,
} from "@/lib/explanation";
import { RULE_CRITERIA, type MatchResult, type MatchedSkill, type RuleCriterion, type Worker } from "@/lib/types";
import styles from "./Explanation.module.css";

export const NOT_ASSESSED = "Not assessed";

const CRITERION_LABEL: Record<RuleCriterion, string> = {
  skill_overlap: "Skill overlap",
  location: "Location",
  budget_fit: "Budget fit",
  availability: "Availability",
};

const PROVENANCE: Record<MatchedSkill["source"], { icon: string; label: (origin: string | null) => string }> = {
  listed: { icon: "✓", label: () => "Listed by you" },
  text: { icon: "✎", label: () => "Your own words" },
  informal_term: { icon: "⇄", label: (origin) => `Inferred via ${origin ?? "your wording"}` },
  occupation_label: { icon: "⚙", label: (origin) => `Inferred via occupation: ${origin ?? "your trade"}` },
};

export function ProvenanceBadge({ skill }: { skill: MatchedSkill }) {
  const description = PROVENANCE[skill.source];
  if (!description) return <span className={`${styles.provenance} ${styles.unknown}`}>Matched</span>;
  const origin =
    skill.source === "informal_term"
      ? (skill.graph_path[0]?.source.label ?? null)
      : (skill.graph_path.at(-1)?.source.label ?? null);
  return (
    <span className={`${styles.provenance} ${styles[skill.source]}`}>
      <span aria-hidden="true">{description.icon}</span>
      {description.label(origin)}
    </span>
  );
}

/** A score out of 100, or "Not assessed" when the engine had nothing to compare. */
export function CriterionValue({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className={styles.notAssessed} title="The information is missing from your profile or from the job">
        {NOT_ASSESSED}
      </span>
    );
  }
  return <span className={styles.criterionValue}>{Math.round(value * 100)}</span>;
}

function ScoreBar({ label, value, caption }: { label: string; value: number | null; caption: string }) {
  if (value === null) {
    return (
      <div className={styles.scoreBlock}>
        <p className={styles.scoreLabel}>
          {label} <span className={styles.notAssessed}>{NOT_ASSESSED}</span>
        </p>
        <p className={styles.caption}>{caption}</p>
      </div>
    );
  }
  return (
    <div className={styles.scoreBlock}>
      <p className={styles.scoreLabel}>
        {label} {Math.round(value * 100)}
      </p>
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
      </div>
      <p className={styles.caption}>{caption}</p>
    </div>
  );
}

export function PlainExplanation({ result, worker }: { result: MatchResult; worker: Worker }) {
  const lined = whatLinedUp(result, worker);
  const unchecked = whatWeCouldNotCheck(result, worker);
  const note = vocabularyNote(result);

  return (
    <>
      <h2 className={styles.heading}>What lined up</h2>
      <div className="card">
        {lined.length === 0 ? (
          <p className={styles.muted}>Nothing specific lined up; this job was matched on wording alone.</p>
        ) : (
          <ul className={styles.list}>
            {lined.map((line) => (
              <li key={line} className={styles.item}>
                <span className={`${styles.marker} ${styles.tick}`} aria-hidden="true">
                  ✓
                </span>
                {line}
              </li>
            ))}
          </ul>
        )}
      </div>

      {unchecked.length > 0 && (
        <>
          <h2 className={styles.heading}>What we couldn&apos;t check</h2>
          <div className="card">
            <ul className={styles.list}>
              {unchecked.map((line) => (
                <li key={line} className={styles.item}>
                  <span className={`${styles.marker} ${styles.dot}`} aria-hidden="true" />
                  {line}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {note && (
        <div className={styles.vocabulary}>
          <span className={styles.vocabularyIcon} aria-hidden="true">
            ⇄
          </span>
          <span>
            You described yourself as a <span className="mono">{note.term}</span>. We matched that to the trade{" "}
            <span className="mono">{note.occupation}</span>
            {tradePhrase(note.occupation) ? "" : ""}.
          </span>
        </div>
      )}
    </>
  );
}

export function TechnicalDetail({ result }: { result: MatchResult }) {
  const [open, setOpen] = useState(false);
  const components = result.rule_components;
  const trace = graphTrace(result);

  return (
    <section>
      <button type="button" className={styles.disclosure} onClick={() => setOpen((shown) => !shown)} aria-expanded={open}>
        <span aria-hidden="true">{open ? "▾" : "▸"}</span> See the technical detail
      </button>

      {open && (
        <div className="card">
          <ScoreBar
            label="Rule-based score"
            value={result.scores.rule}
            caption="Compares your skills, location, rate and availability against the job"
          />
          <ScoreBar
            label="Semantic score"
            value={result.scores.semantic}
            caption="Compares the meaning of your description with the job description"
          />

          <h3 className={styles.subheading}>Matched skills</h3>
          {result.matched_skills.length === 0 ? (
            <p className={styles.muted}>No skill was shared with this job.</p>
          ) : (
            <ul className={styles.skills}>
              {result.matched_skills.map((skill) => (
                <li key={skill.skill} className={styles.skillRow}>
                  <span>{skill.skill_label}</span>
                  <ProvenanceBadge skill={skill} />
                </li>
              ))}
            </ul>
          )}

          <h3 className={styles.subheading}>Criteria</h3>
          <ul className={styles.criteria}>
            {RULE_CRITERIA.map((criterion) => (
              <li key={criterion} className={styles.criterionRow}>
                <span>{CRITERION_LABEL[criterion]}</span>
                <CriterionValue value={components ? components[criterion] : null} />
              </li>
            ))}
          </ul>

          {trace && <pre className={`mono ${styles.trace}`}>{trace}</pre>}
        </div>
      )}
    </section>
  );
}
