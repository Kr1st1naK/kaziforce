"use client";

/** One ranked job, as on the matches screen: rank, title, facts, skill chips, score band. */

import Link from "next/link";
import type { Band, MatchResult } from "@/lib/types";
import styles from "./MatchCard.module.css";

const BAND_LABEL: Record<Band, string> = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
  below_threshold: "Below threshold",
};

const CHIPS_SHOWN = 3;

export function formatKes(amount: number | null): string {
  return amount === null ? "Not stated" : `KES ${amount.toLocaleString("en-KE")} / day`;
}

/** A dot plus a word: the band is never carried by colour alone. */
export function MatchScoreBadge({ score, band }: { score: number; band: Band }) {
  return (
    <span className={styles.badge}>
      <span className={styles.badgeScore}>Match score {score}</span>
      <span className={`${styles.dot} ${styles[band]}`} aria-hidden="true" />
      <span className={styles[band]}>{BAND_LABEL[band]}</span>
    </span>
  );
}

/**
 * The first few matched skills as chips. When more matched than are shown, "+N more" is a link to
 * `moreHref` (the match's "Why this job?" page, which lists every one), not plain text that only looks tappable.
 */
export function SkillChips({ skills, shown = CHIPS_SHOWN, moreHref }: { skills: string[]; shown?: number; moreHref?: string }) {
  const visible = skills.slice(0, shown);
  const hidden = skills.length - visible.length;
  return (
    <div className={styles.chips}>
      {visible.map((skill) => (
        <span key={skill} className={`mono ${styles.chip}`}>
          {skill}
        </span>
      ))}
      {hidden > 0 &&
        (moreHref ? (
          <Link className={`${styles.more} ${styles.moreLink}`} href={moreHref} aria-label={`+${hidden} more matched skills`}>
            +{hidden} more
          </Link>
        ) : (
          <span className={styles.more}>+{hidden} more</span>
        ))}
    </div>
  );
}

export function MatchCard({ result, href }: { result: MatchResult; href: string }) {
  return (
    <article className={`card ${styles.card}`}>
      <div className={styles.top}>
        <span className={styles.rank}>#{result.rank}</span>
        <div className={styles.headline}>
          <h3 className={styles.title}>{result.title}</h3>
          <p className={styles.facts}>
            {[result.location ?? "Not stated", formatKes(result.budget), result.availability ?? "Not stated"].join(
              " · ",
            )}
          </p>
        </div>
        <MatchScoreBadge score={result.match_score} band={result.band} />
      </div>
      <div className={styles.bottom}>
        <SkillChips skills={result.matched_skills.map((skill) => skill.skill_label)} moreHref={href} />
        <Link className={`button button-secondary ${styles.why}`} href={href}>
          Why this job?
        </Link>
      </div>
    </article>
  );
}
