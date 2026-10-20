/**
 * The only place a score is turned into text or a bar.
 *
 * A score of `null` means the API did not assess it: the configuration has no
 * such component, or the field is missing on the profile or the posting. It is
 * shown as "Not assessed" and never as 0, and a null bar is drawn as an empty
 * hatched track rather than a zero-width fill, so "absent" cannot be mistaken
 * for "scored zero" (docs/api.md, "null means not assessed").
 */

import styles from "./ScoreValue.module.css";

export const NOT_ASSESSED = "Not assessed";
export const NOT_ASSESSED_REASON =
  "Not used by this configuration, or the information is missing from the profile or the posting";

export function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function ScoreValue({ value, className }: { value: number | null; className?: string }) {
  if (value === null) {
    return (
      <span className={[styles.absent, className].filter(Boolean).join(" ")} title={NOT_ASSESSED_REASON}>
        {NOT_ASSESSED}
      </span>
    );
  }
  return <span className={className}>{formatScore(value)}</span>;
}

export function ScoreBar({
  label,
  value,
  variant = "rule",
}: {
  label: string;
  value: number | null;
  variant?: "rule" | "semantic" | "composite";
}) {
  const absent = value === null;
  return (
    <div className={styles.row}>
      <div className={styles.label}>
        <span>{label}</span>
        <ScoreValue value={value} className={styles.value} />
      </div>
      <div
        className={absent ? styles.trackAbsent : styles.track}
        role="img"
        aria-label={`${label}: ${absent ? NOT_ASSESSED : formatScore(value)}`}
        title={absent ? NOT_ASSESSED_REASON : undefined}
      >
        {!absent && (
          <div className={styles[variant]} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
        )}
      </div>
    </div>
  );
}
