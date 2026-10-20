"use client";

/** Skills as chips, added with Enter or a comma. The API accepts at most 50 entries of 200 characters. */

import { useState } from "react";
import { TextField } from "./Field";
import styles from "./SkillsInput.module.css";

export const MAX_SKILLS = 50;
export const MAX_SKILL_LENGTH = 200;

export function SkillsInput({
  label,
  skills,
  onChange,
  hint,
  error,
  disabled,
  placeholder,
}: {
  label: string;
  skills: string[];
  onChange: (skills: string[]) => void;
  hint?: string;
  error?: string;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");

  const add = (text: string) => {
    const entries = text
      .split(",")
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0 && entry.length <= MAX_SKILL_LENGTH);
    const next = [...skills];
    for (const entry of entries) {
      if (next.length >= MAX_SKILLS) break;
      if (!next.some((existing) => existing.toLowerCase() === entry.toLowerCase())) next.push(entry);
    }
    onChange(next);
    setDraft("");
  };

  return (
    <div>
      {skills.length > 0 ? (
        <ul className={styles.chips}>
          {skills.map((skill) => (
            <li key={skill} className={styles.chip}>
              <span>{skill}</span>
              <button
                type="button"
                className={styles.remove}
                aria-label={`Remove ${skill}`}
                disabled={disabled}
                onClick={() => onChange(skills.filter((existing) => existing !== skill))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>No skills added yet.</p>
      )}
      <TextField
        label={label}
        value={draft}
        onChange={(value) => (value.endsWith(",") ? add(value) : setDraft(value))}
        onKeyDownEnter={() => add(draft)}
        disabled={disabled || skills.length >= MAX_SKILLS}
        maxLength={MAX_SKILL_LENGTH}
        placeholder={placeholder}
        hint={hint ?? `Press Enter or type a comma to add one. ${skills.length} of ${MAX_SKILLS} added.`}
        error={error}
        optional
      />
    </div>
  );
}
