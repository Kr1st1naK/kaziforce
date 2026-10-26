"use client";

/**
 * The worker's ranked jobs (FR-08).
 *
 * Only matches at or above the display threshold are shown. If none reaches it,
 * the screen says so plainly rather than listing weak matches — the threshold
 * is presentation only and changes no score (docs/scoring-policy.md §6).
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MatchCard } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard, useSession } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import styles from "./page.module.css";

const TOP_K = 10;

export default function Page() {
  const waiting = useGuard("worker");
  const { session } = useSession();
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasProfile = Boolean(session?.worker_profile_id);

  useEffect(() => {
    if (!hasProfile) return;
    let cancelled = false;
    api
      .myMatches(TOP_K)
      .then((result) => !cancelled && setRecommendation(result))
      .catch((caught) => !cancelled && setError(ApiErrorMessage(caught)));
    return () => {
      cancelled = true;
    };
  }, [hasProfile]);

  if (waiting) return null;

  const shown = recommendation?.results.filter((result) => result.band !== "below_threshold") ?? [];

  return (
    <AppShell>
      <h1>Your matches</h1>
      <p className={`subtitle ${styles.subtitle}`}>Jobs ranked by how well they fit your profile.</p>

      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}

      {!error && !recommendation && (
        <p className={styles.loading} role="status" aria-live="polite">
          Finding jobs that suit you…
        </p>
      )}

      {recommendation && shown.length === 0 && (
        <div className={`card ${styles.empty}`}>
          <h2 className={styles.emptyHeading}>No strong matches yet</h2>
          <p className={styles.emptyBody}>
            We didn&apos;t find a job that fits your profile well. Adding more detail about your skills usually helps.
          </p>
          <Link className="button" href="/worker/profile">
            Edit your profile
          </Link>
        </div>
      )}

      {shown.map((result) => (
        <MatchCard key={result.posting_id} result={result} href={`/worker/matches/${result.posting_id}`} />
      ))}
    </AppShell>
  );
}
