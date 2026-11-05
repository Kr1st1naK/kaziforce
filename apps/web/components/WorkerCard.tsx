/**
 * One worker, as a client may see them: what they wrote about their work, the trade the
 * system read it as, and the practical facts.
 *
 * A worker who has a name and has agreed to be shown also has it here, as a link to their
 * profile. Everyone else is anonymous, as before. Being named says that a worker can be
 * contacted, not that they fit: there is no score, no rank and no number, the cards are
 * listed in the order the API returned them (which carries no meaning), and a named card
 * is drawn no larger and no earlier than an anonymous one. Job-to-worker matching is out of
 * scope, and there is no evaluation behind any ordering of workers
 * (docs/limitations.md, "A client is shown an unordered sample").
 */

import Link from "next/link";
import type { TradeWorker } from "@/lib/types";
import { formatKes } from "./MatchCard";
import styles from "./WorkerCard.module.css";

export function WorkerCard({ worker, trade, postingId }: { worker: TradeWorker; trade: string; postingId?: string }) {
  // `posting` lets the profile page link back to the job the client came from.
  const href = worker.public_id
    ? `/client/workers/${worker.public_id}${postingId ? `?posting=${encodeURIComponent(postingId)}` : ""}`
    : null;

  return (
    <article className={styles.card}>
      {href && worker.name && (
        <Link className={styles.name} href={href}>
          {worker.name}
        </Link>
      )}
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
