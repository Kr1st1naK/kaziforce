"use client";

/**
 * Screen 05: your job posting is live (wireframe 05).
 *
 * Shows the occupation the posting was understood as, the skills it states,
 * and how many registered workers match. Skills the knowledge graph could
 * infer from the occupation are deliberately not shown: matching uses stated
 * requirements only, so listing inferred ones would imply they count
 * (docs/scoring-policy.md §1).
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { EnrichmentSummary } from "@/components/EnrichmentSummary";
import { formatKes } from "@/components/MatchCard";
import { ApiError, api } from "@/lib/api";
import type { JobInterpretation } from "@/lib/types";
import styles from "./page.module.css";

export default function Page({ params }: { params: Promise<{ postingId: string }> }) {
  // The heading is in the static shell; the posting waits on the route parameter.
  return (
    <div className="panel">
      <h1>Your job posting is live</h1>
      <Suspense
        fallback={
          <p role="status" aria-live="polite">
            Loading…
          </p>
        }
      >
        <Posting params={params} />
      </Suspense>
    </div>
  );
}

function Posting({ params }: { params: Promise<{ postingId: string }> }) {
  const { postingId } = use(params);
  const [data, setData] = useState<JobInterpretation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .job(postingId)
      .then((result) => !cancelled && setData(result))
      .catch((caught) => {
        if (cancelled) return;
        setError(
          caught instanceof ApiError && caught.code === "not_found"
            ? "That posting could not be found."
            : caught instanceof ApiError
              ? caught.message
              : "Something went wrong.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [postingId]);

  if (error) {
    return (
      <>
        <div className="alert" role="alert">
          {error}
        </div>
        <Link className="button" href="/jobs/new">
          Post another job
        </Link>
      </>
    );
  }

  if (!data) {
    return (
      <p role="status" aria-live="polite">
        Loading…
      </p>
    );
  }

  const { job, interpretation, candidate_jobs } = data;
  const pool = interpretation.worker_pool;

  return (
    <>
      <p className={styles.headline}>
        <strong>{job.title}</strong>
        <br />
        {job.location ?? "No location stated"} · {formatKes(job.budget)} ·{" "}
        {job.availability ?? "No availability stated"}
      </p>

      <div className="section">
        <h2>How we understood your posting</h2>
        <EnrichmentSummary enrichment={interpretation} subject="posting" />
      </div>

      <div className="section">
        <h2>Required skills you listed</h2>
        {interpretation.stated_skills.length === 0 ? (
          <p className="note" style={{ marginBottom: 0 }}>
            You listed no skills, so this posting will be matched on its wording alone.
          </p>
        ) : (
          <>
            <ul className={styles.skills}>
              {interpretation.stated_skills.map((skill) => (
                <li key={skill.skill} className={styles.skillRow}>
                  <span className={styles.skillLabel}>{skill.skill_label}</span>
                  <span className={`${styles.tag} ${skill.source === "text" ? styles.tagText : ""}`}>
                    {skill.source === "listed" ? "recognised skill" : "your own words"}
                  </span>
                </li>
              ))}
            </ul>
            <p className="note" style={{ margin: "14px 0 0" }}>
              These are the skills you listed. Matching uses these only.
            </p>
          </>
        )}
      </div>

      <div className="section">
        <h2>Worker pool</h2>
        {pool.length === 0 ? (
          <p className={styles.pool}>
            No occupation was recognised, so we cannot say how many workers match yet.
          </p>
        ) : (
          pool.map((entry) => (
            <p key={entry.occupation.id} className={styles.pool}>
              <span className={styles.poolCount}>{entry.workers}</span> workers whose profiles match the{" "}
              {entry.occupation.label} occupation.
            </p>
          ))
        )}
        <p className="note" style={{ margin: "14px 0 0" }}>
          Your posting joined a pool of {candidate_jobs} jobs that workers are matched against.
        </p>
      </div>

      <div className="actions">
        <Link className="button" href="/jobs/new">
          Post another job
        </Link>
      </div>
    </>
  );
}
