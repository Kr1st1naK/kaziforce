"use client";

/**
 * Your job has been posted: how the posting was understood, and who works in
 * that trade.
 *
 * Only the skills the client listed are shown. Skills the knowledge graph could
 * infer from the trade are deliberately left out, because matching uses stated
 * requirements only (docs/scoring-policy.md §1). The worker list carries no
 * score and no ranking.
 *
 * How the posting was read is said in plain sentences, in the open — not behind a
 * disclosure control and not in the engine's own vocabulary. This is the same
 * decision the worker's explanation screen makes (components/Explanation.tsx):
 * a client judging whether we understood them is not helped by the name of the
 * taxonomy we consulted.
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ApiErrorMessage, useGuard } from "@/components/SessionProvider";
import { WorkerCard } from "@/components/WorkerCard";
import { api } from "@/lib/api";
import type { JobInterpretation } from "@/lib/types";
import styles from "./page.module.css";

export default function Page({ params }: { params: Promise<{ postingId: string }> }) {
  const waiting = useGuard("client");
  if (waiting) return null;
  return (
    <AppShell>
      <h1 className={styles.heading}>
        <span className={styles.tick} aria-hidden="true">
          ✓
        </span>
        Your job has been posted.
      </h1>
      <Suspense fallback={<p className={styles.loading}>Loading…</p>}>
        <Posting params={params} />
      </Suspense>
    </AppShell>
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
      .catch((caught) => !cancelled && setError(ApiErrorMessage(caught)));
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
        <Link className={`link ${styles.another}`} href="/client/post">
          <span aria-hidden="true">+</span> Post another job
        </Link>
      </>
    );
  }
  if (!data) {
    return (
      <p className={styles.loading} role="status" aria-live="polite">
        Loading…
      </p>
    );
  }

  const { job, interpretation } = data;
  const trade = interpretation.occupations[0] ?? null;
  const pool = trade ? interpretation.worker_pool.find((entry) => entry.occupation.id === trade.id) : undefined;

  return (
    <>
      <div className={`card ${styles.section}`}>
        <h2 className={styles.sectionHeading}>How we understood your posting</h2>

        <div className={styles.verbatim}>
          <span className={styles.verbatimLabel}>Client verbatim input</span>
          <span className={styles.verbatimText}>&ldquo;{job.title}&rdquo;</span>
        </div>

        <span className={styles.arrow} aria-hidden="true">
          ↓
        </span>

        {trade ? (
          <>
            <p className={styles.matchedTo}>
              We matched this to the trade: <span className={styles.trade}>{trade.label}</span>
            </p>
            <div className={styles.chips}>
              {interpretation.stated_skills.map((skill) => (
                <span key={skill.skill} className={styles.chip}>
                  {skill.skill_label}
                </span>
              ))}
            </div>
          </>
        ) : (
          <p className={styles.matchedTo}>
            We couldn&apos;t match this to a trade we know. Your posting is live and will still be matched on its
            wording.
          </p>
        )}

        <p className={styles.plain}>
          {interpretation.terms.length > 0 ? (
            <>
              You wrote &ldquo;{interpretation.terms[0].label}&rdquo;, which is another way of saying{" "}
              {trade?.label}, so that is the trade we read your posting as.
            </>
          ) : (
            <>
              We read the words of your posting
              {trade ? <> and they describe the work {trade.label}s do</> : null}.
            </>
          )}{" "}
          We match on the skills you listed above, and nothing else.
          {interpretation.unmapped.length > 0 && (
            <>
              {" "}
              We didn&apos;t recognise {interpretation.unmapped.map((entry) => `“${entry}”`).join(", ")}, so we
              kept it exactly as you wrote it.
            </>
          )}
        </p>
      </div>

      {trade && pool && (
        <div className={`card ${styles.section}`}>
          <h2 className={styles.sectionHeading}>Workers in this trade</h2>
          <p className={styles.poolCount}>
            {pool.workers} {pool.workers === 1 ? "worker" : "workers"} on the platform describe themselves as{" "}
            {trade.label}s.
          </p>
          <ul className={styles.workers}>
            {pool.sample.map((worker, index) => (
              <li key={`${index}-${worker.describes_as}`}>
                <WorkerCard worker={worker} trade={trade.label} />
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link className={`link ${styles.another}`} href="/client/post">
        <span aria-hidden="true">+</span> Post another job
      </Link>
    </>
  );
}
