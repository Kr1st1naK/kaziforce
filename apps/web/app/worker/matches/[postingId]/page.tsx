"use client";

/**
 * Why this job suits you (FR-09).
 *
 * The explanation is composed from what the API returns: the matched skills
 * with their provenance, the per-criterion scores, and the two profiles. The
 * ranking is fetched and this posting found in it, so the page works on a
 * direct load or a refresh.
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PlainExplanation, TechnicalDetail } from "@/components/Explanation";
import { ApiErrorMessage, useGuard } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { MatchResult, Worker } from "@/lib/types";
import styles from "./page.module.css";

const SEARCH_DEPTH = 50;
const SCORE_STYLE = { strong: "", moderate: styles.scoreModerate, weak: styles.scoreWeak } as const;
const BAND_WORD = { strong: "Strong", moderate: "Moderate", weak: "Weak", below_threshold: "Below threshold" } as const;

export default function Page({ params }: { params: Promise<{ postingId: string }> }) {
  const waiting = useGuard("worker");
  if (waiting) return null;
  return (
    <AppShell>
      <Link className={styles.back} href="/worker/matches">
        <span aria-hidden="true">←</span> Back to your matches
      </Link>
      <h1 className={styles.heading}>Why this job suits you</h1>
      <Suspense fallback={<p className={styles.loading}>Loading…</p>}>
        <Explanation params={params} />
      </Suspense>
    </AppShell>
  );
}

function Explanation({ params }: { params: Promise<{ postingId: string }> }) {
  const { postingId } = use(params);
  const [found, setFound] = useState<{ result: MatchResult; worker: Worker } | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .myMatches(SEARCH_DEPTH)
      .then((recommendation) => {
        if (cancelled) return;
        const result = recommendation.results.find((candidate) => candidate.posting_id === postingId);
        if (result) setFound({ result, worker: recommendation.worker });
        else setMessage("This job is no longer among your matches.");
      })
      .catch((caught) => !cancelled && setMessage(ApiErrorMessage(caught)));
    return () => {
      cancelled = true;
    };
  }, [postingId]);

  if (message) {
    return (
      <div className="alert" role="alert">
        {message}
      </div>
    );
  }
  if (!found) {
    return (
      <p className={styles.loading} role="status" aria-live="polite">
        Working out the explanation…
      </p>
    );
  }

  const { result, worker } = found;
  const band = result.band === "below_threshold" ? "weak" : result.band;

  return (
    <>
      <div className="card">
        <div className={styles.summary}>
          <span className={styles.pair}>
            Your profile
            <span className={styles.swap} aria-hidden="true">
              ⇄
            </span>
            <span className={styles.jobTitle}>{result.title}</span>
          </span>
          <span className={`${styles.score} ${SCORE_STYLE[band]}`}>
            Match score {result.match_score} — {BAND_WORD[result.band]}
          </span>
        </div>
      </div>

      <PlainExplanation result={result} worker={worker} />
      <TechnicalDetail result={result} />
    </>
  );
}
