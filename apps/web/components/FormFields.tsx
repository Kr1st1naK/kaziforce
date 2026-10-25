"use client";

/** Labelled inputs for the profile and posting forms: label, (required)/(optional), hint, error. */

import { useId } from "react";
import styles from "./FormFields.module.css";

type Base = {
  label: string;
  required?: boolean;
  hint?: string;
  hintIcon?: React.ReactNode;
  error?: string;
  disabled?: boolean;
};

function Label({ label, required, id }: { label: string; required?: boolean; id: string }) {
  return (
    <label className={styles.label} htmlFor={id}>
      {label} <span className={styles.flag}>({required ? "required" : "optional"})</span>
    </label>
  );
}

function Messages({ hint, hintIcon, error, id }: Pick<Base, "hint" | "hintIcon" | "error"> & { id: string }) {
  return (
    <>
      {hint && !error && (
        <span id={`${id}-hint`} className={styles.hint}>
          {hintIcon}
          {hint}
        </span>
      )}
      {error && (
        <span id={`${id}-error`} className={styles.error} role="alert">
          {error}
        </span>
      )}
    </>
  );
}

export function TextArea({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
  maxLength,
  required,
  hint,
  hintIcon,
  error,
  disabled,
}: Base & {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  maxLength?: number;
}) {
  const id = useId();
  return (
    <div className={styles.field}>
      <Label label={label} required={required} id={id} />
      <textarea
        id={id}
        rows={rows}
        maxLength={maxLength}
        placeholder={placeholder}
        className={`${styles.control} ${styles.textarea} ${error ? styles.invalid : ""}`}
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      <Messages hint={hint} hintIcon={hintIcon} error={error} id={id} />
    </div>
  );
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  maxLength,
  required,
  hint,
  error,
  disabled,
}: Base & { value: string; onChange: (value: string) => void; placeholder?: string; maxLength?: number }) {
  const id = useId();
  return (
    <div className={styles.field}>
      <Label label={label} required={required} id={id} />
      <input
        id={id}
        type="text"
        maxLength={maxLength}
        placeholder={placeholder}
        className={`${styles.control} ${error ? styles.invalid : ""}`}
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      <Messages hint={hint} error={error} id={id} />
    </div>
  );
}

export function Select({
  label,
  value,
  onChange,
  options,
  placeholder,
  required,
  hint,
  error,
  disabled,
}: Base & {
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
  placeholder: string;
}) {
  const id = useId();
  return (
    <div className={styles.field}>
      <Label label={label} required={required} id={id} />
      <select
        id={id}
        className={`${styles.control} ${styles.select} ${error ? styles.invalid : ""}`}
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <Messages hint={hint} error={error} id={id} />
    </div>
  );
}

export function AmountInput({
  label,
  value,
  onChange,
  placeholder,
  required,
  hint,
  error,
  disabled,
}: Base & { value: string; onChange: (value: string) => void; placeholder?: string }) {
  const id = useId();
  return (
    <div className={styles.field}>
      <Label label={label} required={required} id={id} />
      <div className={`${styles.amount} ${error ? styles.invalid : ""}`}>
        <span className={styles.currency} aria-hidden="true">
          KES
        </span>
        <input
          id={id}
          type="number"
          min={0}
          step={100}
          inputMode="numeric"
          placeholder={placeholder}
          className={styles.amountInput}
          value={value}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      <Messages hint={hint} error={error} id={id} />
    </div>
  );
}
