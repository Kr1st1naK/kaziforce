"use client";

/** Form field wrappers: one label, one optional hint, one error message tied to the control. */

import { useId } from "react";
import styles from "./Field.module.css";

type Common = {
  label: string;
  error?: string;
  hint?: string;
  optional?: boolean;
  disabled?: boolean;
};

function useFieldIds(error?: string, hint?: string) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined;
  return { id, errorId, hintId, describedBy };
}

function Messages({ error, hint, errorId, hintId }: { error?: string; hint?: string; errorId: string; hintId: string }) {
  return (
    <>
      {hint && (
        <span id={hintId} className={styles.hint}>
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} className={styles.error} role="alert">
          {error}
        </span>
      )}
    </>
  );
}

export function TextField({
  label,
  value,
  onChange,
  error,
  hint,
  optional,
  disabled,
  multiline,
  maxLength,
  placeholder,
  onKeyDownEnter,
}: Common & {
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  maxLength?: number;
  placeholder?: string;
  /** Called instead of submitting the form, so Enter can add a chip. */
  onKeyDownEnter?: () => void;
}) {
  const { id, errorId, hintId, describedBy } = useFieldIds(error, hint);
  const className = `${styles.control} ${multiline ? styles.textarea : ""} ${error ? styles.invalid : ""}`;
  const shared = {
    id,
    value,
    disabled,
    maxLength,
    placeholder,
    className,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(event.target.value),
    onKeyDown: onKeyDownEnter
      ? (event: React.KeyboardEvent) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onKeyDownEnter();
          }
        }
      : undefined,
  };
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label} {optional && <span className={styles.optional}>(optional)</span>}
      </label>
      {multiline ? <textarea rows={4} {...shared} /> : <input type="text" {...shared} />}
      <Messages error={error} hint={hint} errorId={errorId} hintId={hintId} />
    </div>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  error,
  hint,
  optional,
  disabled,
}: Common & {
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
  placeholder: string;
}) {
  const { id, errorId, hintId, describedBy } = useFieldIds(error, hint);
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label} {optional && <span className={styles.optional}>(optional)</span>}
      </label>
      <select
        id={id}
        className={`${styles.control} ${error ? styles.invalid : ""}`}
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <Messages error={error} hint={hint} errorId={errorId} hintId={hintId} />
    </div>
  );
}

export function AmountField({
  label,
  value,
  onChange,
  error,
  hint,
  optional,
  disabled,
}: Common & { value: string; onChange: (value: string) => void }) {
  const { id, errorId, hintId, describedBy } = useFieldIds(error, hint);
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label} {optional && <span className={styles.optional}>(optional)</span>}
      </label>
      <div className={styles.prefixed}>
        <span className={styles.prefix} aria-hidden="true">
          KES
        </span>
        <input
          id={id}
          type="number"
          min={0}
          step={50}
          inputMode="numeric"
          className={`${styles.control} ${error ? styles.invalid : ""}`}
          value={value}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      <Messages error={error} hint={hint} errorId={errorId} hintId={hintId} />
    </div>
  );
}
