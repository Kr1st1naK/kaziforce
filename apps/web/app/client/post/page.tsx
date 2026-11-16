"use client";

/**
 * Post a job (FR-02).
 *
 * No category field: the schema keeps the column, but matching never reads it,
 * so asking for one would imply it affects the result.
 *
 * The form empties itself the moment a posting is accepted. Next keeps this route
 * mounted in a hidden Activity after the client is sent to the confirmation screen,
 * so state left behind here would still be filled in when they come back to post
 * the next job.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { AmountInput, Select, TextArea, TextInput } from "@/components/FormFields";
import { ApiErrorMessage, isNetworkFailure, useGuard, useSession } from "@/components/SessionProvider";
import { FormAlert } from "@/components/FormAlert";
import { ApiError, api } from "@/lib/api";
import { useIdleWhenHidden } from "@/lib/useIdleWhenHidden";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability } from "@/lib/types";
import styles from "./page.module.css";

/**
 * The field holds a working pattern (Full-time, Part-time, Weekends), which the scorer compares with a worker's
 * availability. It is not a date, and the option values are what the API stores. Only the label says so.
 */
const NO_PATTERN = "No fixed pattern";

export default function Page() {
  const waiting = useGuard("client");
  const { refresh } = useSession();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [skills, setSkills] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
  const [location, setLocation] = useState("");
  const [availability, setAvailability] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [retryable, setRetryable] = useState(false); // the last submit got no response: offer "Try again"
  // A successful post leaves this page for the posting's result and stays mounted, hidden; "Post another job" then
  // comes back to it. Clear busy when the page is left, or it returns saying "Posting…" with nothing submitted (U-10).
  useIdleWhenHidden(() => setBusy(false));
  const [confirming, setConfirming] = useState(false);

  const clear = () => {
    setTitle("");
    setSkills("");
    setDescription("");
    setBudget("");
    setLocation("");
    setAvailability("");
    setErrors({});
  };

  const submit = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const found: Record<string, string> = {};
    if (!title.trim()) found.title = "Give the job a short title.";
    if (!description.trim()) found.description = "Say what you need done.";
    if (budget === "") found.budget = "Give a budget per day.";
    if (!location) found.location = "Choose where the job is.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    setRetryable(false);
    try {
      const created = await api.createJob({
        title: title.trim(),
        description: description.trim(),
        required_skills: skills
          .split(",")
          .map((entry) => entry.trim())
          .filter(Boolean),
        location,
        availability: (availability as Availability) || null,
        budget: Number(budget),
      });
      clear();
      await refresh();
      router.push(`/client/postings/${created.posting_id}`);
    } catch (error) {
      setBusy(false);
      setRetryable(isNetworkFailure(error));
      setErrors(
        error instanceof ApiError && error.field
          ? { [error.field]: error.message }
          : { form: ApiErrorMessage(error) },
      );
    }
  };

  if (waiting) return null;

  return (
    <AppShell>
      <h1>Post a job</h1>
      <p className={`subtitle ${styles.subtitle}`}>Say what you need, the way you would to a neighbour.</p>

      <div className="card">
        {errors.form && (
          <FormAlert className={styles.alert} message={errors.form} onRetry={retryable ? () => void submit() : undefined} busy={busy} />
        )}

        <form onSubmit={submit} noValidate>
          <TextArea
            label="What do you need done?"
            required
            value={description}
            onChange={setDescription}
            error={errors.description}
            rows={4}
            maxLength={4000}
            placeholder="e.g. I need a plumber to fix a leaking tap"
            hint="Write it in your own words, in English or Kiswahili. For example: “I need a plumber to fix a leaking tap”, “Electrician needed, a socket keeps sparking” or “fundi bomba wa kurekebisha bomba”."
          />

          <TextInput
            label="Job title"
            required
            value={title}
            onChange={setTitle}
            error={errors.title}
            maxLength={255}
            placeholder="e.g. Fix a leaking tap"
            hint="A few words. Workers see this title."
          />

          <TextArea
            label="Add skills if you know them"
            value={skills}
            onChange={setSkills}
            error={errors.required_skills}
            rows={3}
            placeholder="e.g. replace faucets, plumbing tools"
            hint="Optional. If you leave this empty, we read the trade from what you wrote above."
          />

          <AmountInput
            label="Budget per day"
            required
            value={budget}
            onChange={setBudget}
            placeholder="2500"
            error={errors.budget}
          />

          <div className={styles.row}>
            <Select
              label="Where is the job?"
              required
              value={location}
              onChange={setLocation}
              options={SUGGESTED_LOCATIONS}
              placeholder="Select location"
              error={errors.location}
            />
            <Select
              label="What working pattern does the job need?"
              value={availability}
              onChange={setAvailability}
              options={AVAILABILITY}
              placeholder={NO_PATTERN}
              hint="Compared with when each worker is available."
              error={errors.availability}
            />
          </div>

          <div className={styles.actions}>
            <button type="button" className="link" onClick={() => setConfirming(true)} disabled={busy}>
              Cancel
            </button>
            <button className="button" type="submit" disabled={busy}>
              {busy ? "Posting…" : "Post job"} <span aria-hidden="true">→</span>
            </button>
          </div>
        </form>
      </div>

      {confirming && (
        <ConfirmDialog
          question="Clear this form?"
          detail="Everything you have typed will be removed and you can start again."
          onConfirm={() => {
            clear();
            setConfirming(false);
          }}
          onCancel={() => setConfirming(false)}
        />
      )}
    </AppShell>
  );
}
