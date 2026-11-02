"use client";

/**
 * A yes/no question asked before something the person cannot undo.
 *
 * Deliberately not window.confirm(): that dialog is drawn by the browser, cannot be
 * worded as the rest of the app is worded, and cannot be asserted on in a component
 * test. "No" is the default — it holds focus — because the destructive answer is "Yes".
 */

import { useEffect } from "react";
import styles from "./ConfirmDialog.module.css";

export function ConfirmDialog({
  question,
  detail,
  confirmLabel = "Yes, clear it",
  cancelLabel = "No, keep it",
  onConfirm,
  onCancel,
}: {
  question: string;
  detail?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className={styles.backdrop}>
      <div className={`card ${styles.dialog}`} role="alertdialog" aria-modal="true" aria-label={question}>
        <h2 className={styles.question}>{question}</h2>
        {detail && <p className={styles.detail}>{detail}</p>}
        <div className={styles.actions}>
          <button type="button" className="button button-secondary" onClick={onCancel} autoFocus>
            {cancelLabel}
          </button>
          <button type="button" className="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
