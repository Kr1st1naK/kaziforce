/**
 * One worker, as a client may see them: what they wrote about their work, the trade the
 * system read it as, and the practical facts.
 *
 * No score, no rank and no number. Cards are listed in the order the API returned them,
 * which carries no meaning, and nothing here may suggest otherwise: job-to-worker matching
 * is out of scope, and there is no evaluation behind any ordering of workers
 * (docs/limitations.md, "A client is shown an unordered sample").
 */

import type { TradeWorker } from "@/lib/types";
import { formatKes } from "./MatchCard";
import styles from "./WorkerCard.module.css";

export function WorkerCard({ worker, trade }: { worker: TradeWorker; trade: string }) {
  return (
    <article className={styles.card}>
      <p className={styles.words}>&ldquo;{worker.describes_as}&rdquo;</p>
      <span className={styles.trade}>{trade}</span>
      <p className={styles.facts}>
        <span>{worker.location ?? "Location not stated"}</span>
        <span>{worker.availability ?? "Availability not stated"}</span>
        <span>{worker.rate_expectation === null ? "Rate not stated" : formatKes(worker.rate_expectation)}</span>
      </p>
    </article>
  );
}
