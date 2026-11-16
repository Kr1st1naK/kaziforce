"use client";

/**
 * Why a job suits a worker, in plain words (FR-09).
 *
 * Every sentence here is rendered exactly as the API returned it. The backend
 * generator (apps/api/.../explainability/) is the single source of the wording,
 * and it derives each sentence from the graph paths and score components behind
 * the match. The interface composes nothing.
 *
 * There is no technical-detail section: a worker does not need the component
 * scores or the raw graph path to judge whether a job suits them, and the
 * sentences already carry what those numbers mean. The full structured payload
 * is still returned by the API and is recorded in
 * docs/evidence/explanation_payload.md.
 */

import type { Explanation, Reason } from "@/lib/types";
import styles from "./Explanation.module.css";

/** The informal term the worker used, and the trade it reached, if any skill went that way. */
function vocabularyNote(explanation: Explanation): { term: string; occupation: string } | null {
  const viaTerm = explanation.reasons.find((reason) => reason.term && reason.occupation);
  return viaTerm ? { term: viaTerm.term!, occupation: viaTerm.occupation! } : null;
}

function ReasonList({ reasons, marker }: { reasons: Reason[] | string[]; marker: "tick" | "dot" }) {
  const lines = reasons.map((reason) => (typeof reason === "string" ? reason : reason.text));
  return (
    <ul className={styles.list}>
      {lines.map((line) => (
        <li key={line} className={styles.item}>
          <span className={`${styles.marker} ${styles[marker]}`} aria-hidden="true">
            {marker === "tick" ? "✓" : ""}
          </span>
          {line}
        </li>
      ))}
    </ul>
  );
}

export function PlainExplanation({ explanation }: { explanation: Explanation }) {
  const note = vocabularyNote(explanation);

  return (
    <>
      <h2 className={styles.heading}>What lined up</h2>
      <div className="card">
        {explanation.reasons.length === 0 ? (
          <p className={styles.muted}>Nothing specific lined up; this job was matched on wording alone.</p>
        ) : (
          <ReasonList reasons={explanation.reasons} marker="tick" />
        )}
      </div>

      {explanation.not_assessed.length > 0 && (
        <>
          <h2 className={styles.heading}>What we couldn&apos;t check</h2>
          <div className="card">
            <ReasonList reasons={explanation.not_assessed} marker="dot" />
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
            <span className="mono">{note.occupation}</span>.
          </span>
        </div>
      )}
    </>
  );
}
