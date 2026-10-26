"use client";

/** The controls shared by sign-in and create-account: role toggle, phone number, PIN. */

import { useId, useRef, useState } from "react";
import { ROLES, type Role } from "@/lib/types";
import styles from "./AuthFields.module.css";

const ROLE_LABEL: Record<Role, string> = { worker: "I'm a worker", client: "I'm a client" };
export const PIN_LENGTH = 4;

export function RoleToggle({
  role,
  onChange,
  bordered = true,
  disabled,
}: {
  role: Role;
  onChange: (role: Role) => void;
  bordered?: boolean;
  disabled?: boolean;
}) {
  return (
    <div className={styles.roles} role="radiogroup" aria-label="Are you a worker or a client?">
      {ROLES.map((value) => {
        const selected = value === role;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            className={[styles.role, selected ? styles.roleSelected : bordered ? styles.roleBordered : styles.rolePlain]
              .join(" ")}
            onClick={() => onChange(value)}
          >
            {ROLE_LABEL[value]}
          </button>
        );
      })}
    </div>
  );
}

export function PhoneField({
  value,
  onChange,
  error,
  hint,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        Phone number
      </label>
      <div className={`${styles.phone} ${error ? styles.invalid : ""}`}>
        <span className={styles.prefix} aria-hidden="true">
          +254
        </span>
        <input
          id={id}
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          className={styles.phoneInput}
          placeholder="712 345 678"
          value={value}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      {hint && !error && (
        <span id={`${id}-hint`} className={styles.hint}>
          {hint}
        </span>
      )}
      {error && (
        <span id={`${id}-error`} className={styles.error} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

/** Four single-digit boxes. Typing moves forward, backspace moves back. */
export function PinField({
  label,
  value,
  onChange,
  error,
  disabled,
  showToggle = false,
  autoFocus = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  showToggle?: boolean;
  autoFocus?: boolean;
}) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const boxes = useRef<(HTMLInputElement | null)[]>([]);

  const setDigit = (index: number, digit: string) => {
    const digits = digit.replace(/\D/g, "");
    if (!digits) return;
    const next = (value.slice(0, index) + digits + value.slice(index + digits.length)).slice(0, PIN_LENGTH);
    onChange(next);
    boxes.current[Math.min(index + digits.length, PIN_LENGTH - 1)]?.focus();
  };

  const onKeyDown = (index: number) => (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace") {
      event.preventDefault();
      onChange(value.slice(0, Math.max(0, index - (value[index] ? 0 : 1))) + value.slice(index + 1));
      if (!value[index]) boxes.current[Math.max(0, index - 1)]?.focus();
    }
    if (event.key === "ArrowLeft") boxes.current[Math.max(0, index - 1)]?.focus();
    if (event.key === "ArrowRight") boxes.current[Math.min(PIN_LENGTH - 1, index + 1)]?.focus();
  };

  return (
    <div className={styles.field}>
      <div className={styles.pinHeader}>
        <span className={styles.label} id={id}>
          {label}
        </span>
        {showToggle && (
          <button type="button" className={styles.show} onClick={() => setVisible((shown) => !shown)}>
            {visible ? "Hide" : "Show"}
          </button>
        )}
      </div>
      <div className={styles.pin} role="group" aria-labelledby={id} aria-describedby={error ? `${id}-error` : undefined}>
        {Array.from({ length: PIN_LENGTH }, (_, index) => (
          <input
            key={index}
            ref={(element) => {
              boxes.current[index] = element;
            }}
            type={visible ? "text" : "password"}
            inputMode="numeric"
            maxLength={PIN_LENGTH}
            autoFocus={autoFocus && index === 0}
            className={`${styles.pinBox} ${error ? styles.invalid : ""}`}
            aria-label={`${label}, digit ${index + 1}`}
            value={value[index] ?? ""}
            disabled={disabled}
            onChange={(event) => setDigit(index, event.target.value)}
            onKeyDown={onKeyDown(index)}
          />
        ))}
      </div>
      {error && (
        <span id={`${id}-error`} className={styles.error} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
