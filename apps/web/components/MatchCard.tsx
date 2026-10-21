/** One ranked job (wireframe 03): rank, details, score components, matched skills. */

import Link from "next/link";
import type { MatchResult } from "@/lib/types";
import { MatchedSkillList } from "./SkillBadge";
import { ScoreValue, formatScore } from "./ScoreValue";
import styles from "./MatchCard.module.css";

export function formatKes(amount: number | null): string {
  return amount === null ? "No budget stated" : `KES ${amount.toLocaleString("en-KE")} per day`;
}

export function MatchCard({ result, explanationHref }: { result: MatchResult; explanationHref: string }) {
  const { scores } = result;
  return (
    <article className={styles.card}>
      <div className={styles.rank} aria-label={`Rank ${result.rank}`}>
        #{result.rank}
      </div>
      <div className={styles.body}>
        <h3 className={styles.title}>{result.title}</h3>
        <p className={styles.details}>
          {result.location ?? "No location stated"} · {formatKes(result.budget)} ·{" "}
          {result.availability ?? "No availability stated"}
        </p>
        {result.matched_skills.length > 0 ? (
          <MatchedSkillList skills={result.matched_skills} limit={3} />
        ) : (
          <p className={styles.details}>No shared skills; this job matched on its wording alone.</p>
        )}
      </div>
      <div className={styles.side}>
        <div>
          <div className={styles.composite}>{formatScore(scores.composite)}</div>
          <div className={styles.compositeLabel}>Composite score</div>
        </div>
        <div className={styles.components}>
          Rule <ScoreValue value={scores.rule} /> · Semantic <ScoreValue value={scores.semantic} />
        </div>
        <Link className="button" href={explanationHref}>
          Why this match?
        </Link>
      </div>
    </article>
  );
}
