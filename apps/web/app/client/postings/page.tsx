"use client";

/**
 * The client's postings, where they land when they sign in.
 *
 * There is no design for this screen; the rows reuse the row style of the
 * confirmation screen so nothing new is invented. Each row opens that posting's
 * confirmation view.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { formatKes } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard } from "@/components/SessionProvider";
import { api } from "@/lib/api";
import type { PostingSummary } from "@/lib/types";
import styles from "./page.module.css";

export default function Page() {
  const waiting = useGuard("client");
  const [postings, setPostings] = useState<PostingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (waiting) return;
    let cancelled = false;
    api
      .myPostings()
      .then(({ postings: rows }) => !cancelled && setPostings(rows))
      .catch((caught) => !cancelled && setError(ApiErrorMessage(caught)));
    return () => {
      cancelled = true;
    };
  }, [waiting]);

  if (waiting) return null;

  return (
    <AppShell>
      <h1>My postings</h1>
      <p className={`subtitle ${styles.subtitle}`}>The jobs you have posted.</p>

      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}

      {!error && postings === null && (
        <p className={styles.loading} role="status" aria-live="polite">
          Loading your postings…
        </p>
      )}

      {postings !== null && (
        <div className="card">
          {postings.length === 0 ? (
            <p className={styles.empty}>You haven&apos;t posted a job yet.</p>
          ) : (
            <ul className={styles.rows}>
              {postings.map((posting) => (
                <li key={posting.posting_id}>
                  <Link className={styles.row} href={`/client/postings/${posting.posting_id}`}>
                    <span className={styles.title}>{posting.title}</span>
                    <span className={styles.facts}>
                      {[
                        posting.location ?? "Location not stated",
                        formatKes(posting.budget),
                        posting.availability ?? "No strict timeline",
                      ].join(" · ")}
                      {posting.trades.length > 0 && (
                        <>
                          {" · "}
                          <span className={styles.trade}>{posting.trades[0].label}</span>
                        </>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <div className={styles.actions}>
            <Link className="button" href="/client/post">
              Post a job
            </Link>
          </div>
        </div>
      )}
    </AppShell>
  );
}
