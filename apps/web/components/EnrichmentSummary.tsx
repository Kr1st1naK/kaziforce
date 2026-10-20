/**
 * What the knowledge graph made of a profile or a posting: the terms it
 * recognised, the occupation they map to, and the wording it did not recognise.
 *
 * Unrecognised wording is reported, not hidden: the term is kept and still
 * matched literally (FR-10), and saying so is the honest account of a profile
 * that used a term outside the vocabulary.
 */

import type { Enrichment } from "@/lib/types";
import styles from "./EnrichmentSummary.module.css";

export function EnrichmentSummary({ enrichment, subject }: { enrichment: Enrichment; subject: "profile" | "posting" }) {
  const { terms, occupations, unmapped } = enrichment;
  const owner = subject === "profile" ? "your profile" : "this posting";
  return (
    <div className={styles.summary}>
      {occupations.length > 0 ? (
        <p className={styles.line}>
          Understood as{" "}
          {occupations.map((occupation, index) => (
            <span key={occupation.id}>
              {index > 0 && ", "}
              <span className={styles.term}>{occupation.label}</span>
            </span>
          ))}
          {terms.length > 0 && (
            <>
              , from the wording{" "}
              {terms.map((term, index) => (
                <span key={term.id}>
                  {index > 0 && ", "}
                  <span className={styles.quote}>“{term.label}”</span>
                </span>
              ))}
            </>
          )}
          .
        </p>
      ) : (
        <p className={styles.line}>
          No occupation was recognised in {owner}, so matching falls back to the words themselves.
        </p>
      )}
      {unmapped.length > 0 && (
        <p className={`${styles.line} ${styles.unmapped}`}>
          Not recognised:{" "}
          {unmapped.map((entry, index) => (
            <span key={entry}>
              {index > 0 && ", "}
              <span className={styles.quote}>“{entry}”</span>
            </span>
          ))}
          . {unmapped.length === 1 ? "It is kept" : "They are kept"} as written and matched word for word.
        </p>
      )}
    </div>
  );
}
