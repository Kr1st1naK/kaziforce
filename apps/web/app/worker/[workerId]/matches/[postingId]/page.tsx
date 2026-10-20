"use client";

/**
 * Screen 04: why this match? (FR-09, wireframe 04)
 *
 * Fetches the worker's ranking and finds this posting in it, so the page works
 * on a direct load or a refresh. A posting outside the top 50 is reported as
 * such rather than guessed at.
 */

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { CriteriaList } from "@/components/CriteriaList";
import { GraphPath } from "@/components/GraphPath";
import { ScoreBar, ScoreValue, formatScore } from "@/components/ScoreValue";
import { SkillBadge } from "@/components/SkillBadge";
import { formatKes } from "@/components/MatchCard";
import { ApiError, api } from "@/lib/api";
import type { MatchResult } from "@/lib/types";
import styles from "./page.module.css";

const SEARCH_DEPTH = 50;

export default function Page({ params }: { params: Promise<{ workerId: string; postingId: string }> }) {
  // The heading is in the static shell; the explanation waits on the route parameters.
  return (
    <div className="panel">
      <h1>Why this match?</h1>
      <Suspense
        fallback={
          <p role="status" aria-live="polite">
            Loading…
          </p>
        }
      >
        <Explanation params={params} />
      </Suspense>
    </div>
  );
}

function Explanation({ params }: { params: Promise<{ workerId: string; postingId: string }> }) {
  const { workerId, postingId } = use(params);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .recommend(workerId, SEARCH_DEPTH)
      .then((recommendation) => {
        if (cancelled) return;
        const found = recommendation.results.find((candidate) => candidate.posting_id === postingId);
        if (found) {
          setResult(found);
          setStatus("ready");
        } else {
          setStatus("missing");
        }
      })
      .catch((caught) => {
        if (cancelled) return;
        setStatus("error");
        setMessage(caught instanceof ApiError ? caught.message : "Something went wrong.");
      });
    return () => {
      cancelled = true;
    };
  }, [workerId, postingId]);

  const backToMatches = (
    <Link className="button" href={`/worker/${workerId}/matches`}>
      Back to matches
    </Link>
  );

  if (status === "loading") {
    return (
      <p role="status" aria-live="polite">
        Working out the explanation…
      </p>
    );
  }

  if (status !== "ready" || !result) {
    return (
      <>
        <div className="alert" role="alert">
          {status === "missing"
            ? `This job is not in your top ${SEARCH_DEPTH} matches, so there is no ranking to explain.`
            : message}
        </div>
        {backToMatches}
      </>
    );
  }

  const { scores } = result;

  return (
    <>
      <p className={styles.pair}>
        Your profile &nbsp;↔&nbsp; <strong>{result.title}</strong>
      </p>

      <div className="section">
        <div className={styles.summary}>
          <span>Composite score</span>
          <span className={styles.composite}>{formatScore(scores.composite)}</span>
        </div>
      </div>

      <div className="section">
        <h2>Score breakdown</h2>
        <ScoreBar label="Rule-based score" value={scores.rule} variant="rule" />
        <ScoreBar label="Semantic score" value={scores.semantic} variant="semantic" />
        <p className="note" style={{ marginTop: 16, marginBottom: 0 }}>
          The composite score is half the rule-based score plus half the semantic score. The rule-based score
          compares the facts below; the semantic score compares the wording of your profile and the job.
        </p>
      </div>

      <div className="section">
        <h2>How each criterion scored</h2>
        <CriteriaList result={result} />
      </div>

      <div className="section">
        <h2>Matched skills, and where they came from</h2>
        {result.matched_skills.length === 0 ? (
          <p className="note" style={{ marginBottom: 0 }}>
            No skill was shared with this job. It was ranked on the wording of your profile alone.
          </p>
        ) : (
          result.matched_skills.map((skill) => (
            <div key={skill.skill} className={styles.skill}>
              <div className={styles.skillHead}>
                <span className={styles.skillLabel}>{skill.skill_label}</span>
                <SkillBadge skill={skill} />
              </div>
              <GraphPath skill={skill} jobTitle={result.title} />
            </div>
          ))
        )}
      </div>

      <div className="section">
        <h2>The job</h2>
        <p className={styles.details}>
          {result.location ?? "No location stated"} · {formatKes(result.budget)} ·{" "}
          {result.availability ?? "No availability stated"} · ranked #{result.rank}, composite{" "}
          <ScoreValue value={scores.composite} />
        </p>
        <p className={styles.jobText}>{result.description}</p>
      </div>

      <div className="actions">{backToMatches}</div>
    </>
  );
}
