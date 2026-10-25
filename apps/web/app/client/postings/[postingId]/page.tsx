"use client";

/**
 * Your job has been posted: how the posting was understood, and who works in
 * that trade.
 *
 * Only the skills the client listed are shown. Skills the knowledge graph could
 * infer from the trade are deliberately left out, because matching uses stated
 * requirements only (docs/scoring-policy.md §1). The worker list carries no
 * score and no ranking.
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { formatKes } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { JobInterpretation, TradeWorker } from "@/lib/types";
import styles from "./page.module.css";

function workerLine(worker: TradeWorker): string {
  return [
    worker.describes_as,
    worker.location ?? "Location not stated",
    worker.availability ?? "Availability not stated",
    worker.rate_expectation === null ? "Rate not stated" : formatKes(worker.rate_expectation),
  ].join(" · ");
}

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
  const [showWorking, setShowWorking] = useState(false);

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

        <button
          type="button"
          className={styles.disclosure}
          onClick={() => setShowWorking((shown) => !shown)}
          aria-expanded={showWorking}
        >
          <span aria-hidden="true">{showWorking ? "▾" : "▸"}</span> See how we got there
        </button>

        {showWorking && (
          <p className={styles.howWeGotThere}>
            {interpretation.terms.length > 0 ? (
              <>
                You wrote <span className="mono">{interpretation.terms[0].label}</span>, which our trade vocabulary maps
                to <span className="mono">{trade?.label}</span>. The skills above are the ones you listed; matching uses
                those only.
              </>
            ) : (
              <>
                We read the words of your posting against the ESCO trade taxonomy
                {trade ? (
                  <>
                    {" "}
                    and matched <span className="mono">{trade.label}</span>
                  </>
                ) : null}
                . The skills above are the ones you listed; matching uses those only.
              </>
            )}
            {interpretation.unmapped.length > 0 && (
              <>
                {" "}
                We didn&apos;t recognise {interpretation.unmapped.map((entry) => `“${entry}”`).join(", ")}, so we kept
                it as written.
              </>
            )}
          </p>
        )}
      </div>

      {trade && pool && (
        <div className={`card ${styles.section}`}>
          <h2 className={styles.sectionHeading}>Workers in this trade</h2>
          <p className={styles.poolCount}>
            {pool.workers} {pool.workers === 1 ? "worker" : "workers"} on the platform describe themselves as{" "}
            {trade.label}s.
          </p>
          <ul className={styles.workers}>
            {pool.sample.map((worker) => (
              <li key={workerLine(worker)} className={styles.worker}>
                {workerLine(worker)}
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
