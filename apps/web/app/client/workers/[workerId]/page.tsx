"use client";

/**
 * A worker's profile, for a client who has found them on a job's confirmation screen: their
 * name, trade, the practical facts, their own words, and a phone number to ring.
 *
 * It is here only because the worker agreed to it at sign-up, and a worker who withdraws
 * disappears from this page at once: the API answers "not available" and this says so, with no
 * hint of whether the worker ever existed. Contact is by phone and nothing else; there is no
 * in-app messaging. No score and no rank, here or anywhere on the way here.
 */

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { formatKes } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import { formatPhone } from "@/lib/phone";
import type { ClientWorkerView } from "@/lib/types";
import styles from "./page.module.css";

const POSTING_ID = /^[0-9a-f-]{36}$/i;

type Result = { worker: ClientWorkerView } | { message: string };

export default function Page({ params }: { params: Promise<{ workerId: string }> }) {
  const waiting = useGuard("client");
  if (waiting) return null;
  return (
    <AppShell>
      <Suspense fallback={<p className={styles.loading}>Loading…</p>}>
        <Profile params={params} />
      </Suspense>
    </AppShell>
  );
}

function Profile({ params }: { params: Promise<{ workerId: string }> }) {
  const { workerId } = use(params);
  const posting = useSearchParams().get("posting");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .clientWorker(workerId)
      .then((worker) => !cancelled && setResult({ worker }))
      .catch((caught) => {
        if (cancelled) return;
        setResult({
          message:
            caught instanceof ApiError && caught.status === 404
              ? "This worker's profile is not available. They may have chosen not to share it."
              : caught instanceof ApiError && caught.code === "rate_limited"
                ? "You are viewing profiles too quickly. Wait a minute and try again."
                : ApiErrorMessage(caught),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [workerId]);

  // Only a posting id is accepted, so the link back can only ever lead to one of the client's own postings.
  const back =
    posting && POSTING_ID.test(posting)
      ? { href: `/client/postings/${posting}`, label: "Back to your job posting" }
      : { href: "/client/postings", label: "Back to my postings" };

  return (
    <>
      <Link className={`link ${styles.back}`} href={back.href}>
        <span aria-hidden="true">←</span> {back.label}
      </Link>

      {result === null && (
        <p className={styles.loading} role="status" aria-live="polite">
          Loading…
        </p>
      )}

      {result !== null && "message" in result && (
        <div className="alert" role="alert">
          {result.message}
        </div>
      )}

      {result !== null && "worker" in result && <WorkerProfile worker={result.worker} />}
    </>
  );
}

function WorkerProfile({ worker }: { worker: ClientWorkerView }) {
  const name = `${worker.first_name} ${worker.last_name}`;
  const display = `+254 ${formatPhone(worker.contact.phone_local)}`;
  return (
    <>
      <h1 className={styles.name}>{name}</h1>
      {worker.trade && <span className={styles.trade}>{worker.trade}</span>}

      <div className={`card ${styles.section}`}>
        <h2 className={styles.sectionHeading}>Contact {worker.first_name}</h2>
        <p className={styles.phone}>
          <a href={`tel:${worker.contact.phone_e164}`} aria-label={`Call ${name} on ${display}`}>
            {display}
          </a>
        </p>
        <p className={styles.note}>
          {worker.first_name} agreed to share this with clients who post a job in their trade. Please use it only to
          talk about work.
        </p>
      </div>

      <div className={`card ${styles.section}`}>
        <h2 className={styles.sectionHeading}>In their own words</h2>
        {worker.skills.length > 0 && <p className={styles.words}>&ldquo;{worker.skills.join(", ")}&rdquo;</p>}
        <p className={styles.about}>{worker.biography}</p>
      </div>

      <div className={`card ${styles.section}`}>
        <h2 className={styles.sectionHeading}>Details</h2>
        <dl className={styles.details}>
          <div>
            <dt>Where they work</dt>
            <dd>{worker.location ?? "Not stated"}</dd>
          </div>
          <div>
            <dt>When they can work</dt>
            <dd>{worker.availability ?? "Not stated"}</dd>
          </div>
          <div>
            <dt>Daily rate</dt>
            <dd>{formatKes(worker.rate_expectation)}</dd>
          </div>
        </dl>
      </div>
    </>
  );
}
