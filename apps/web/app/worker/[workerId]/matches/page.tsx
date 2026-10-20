"use client";

/**
 * Screen 03: ranked jobs for one worker (FR-08, wireframe 03).
 *
 * The worker's identifier is in the URL, so the page survives a refresh and
 * can be shared, with nothing kept in browser storage.
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { EnrichmentSummary } from "@/components/EnrichmentSummary";
import { MatchCard } from "@/components/MatchCard";
import { ApiError, api } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import styles from "./page.module.css";

const TOP_K = 10;

export default function Page({ params }: { params: Promise<{ workerId: string }> }) {
  // The heading is in the static shell; only the ranking waits on the route parameter.
  return (
    <div className="panel">
      <h1>Your matches</h1>
      <Suspense
        fallback={
          <p className={styles.loading} role="status" aria-live="polite">
            Loading your profile…
          </p>
        }
      >
        <Matches params={params} />
      </Suspense>
    </div>
  );
}

function Matches({ params }: { params: Promise<{ workerId: string }> }) {
  const { workerId } = use(params);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .recommend(workerId, TOP_K)
      .then((result) => !cancelled && setRecommendation(result))
      .catch((caught) => {
        if (cancelled) return;
        setError(caught instanceof ApiError ? caught : new ApiError(0, "internal_error", "Something went wrong."));
      });
    return () => {
      cancelled = true;
    };
  }, [workerId]);

  if (error) {
    return (
      <>
        <div className="alert" role="alert">
          {error.code === "not_found"
            ? "That profile could not be found. It may have been created on a different server."
            : error.message}
        </div>
        <Link className="button" href="/worker">
          Create a profile
        </Link>
      </>
    );
  }

  if (!recommendation) {
    return (
      <p className={styles.loading} role="status" aria-live="polite">
        Ranking jobs for you…
      </p>
    );
  }

  const { results, enrichment, worker, timing_ms } = recommendation;

  return (
    <>
      <p className="note">
        The {results.length} best jobs for your profile, each with the reason it was matched.
      </p>

      <div className="section">
        <h2>How we read your profile</h2>
        <EnrichmentSummary enrichment={enrichment} subject="profile" />
      </div>

      <div className={styles.meta}>
        <span>{worker.location ?? "No location given"}</span>
        <span>{worker.availability ?? "No availability given"}</span>
        <span>Ranked in {Math.round(timing_ms)} ms</span>
      </div>

      {results.length === 0 ? (
        <p className={styles.empty}>No jobs to show yet.</p>
      ) : (
        results.map((result) => (
          <MatchCard
            key={result.posting_id}
            result={result}
            explanationHref={`/worker/${workerId}/matches/${result.posting_id}`}
          />
        ))
      )}

      <div className="actions">
        <Link className="button" href="/worker">
          Change your profile
        </Link>
      </div>
    </>
  );
}
