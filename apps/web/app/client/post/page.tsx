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
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability } from "@/lib/types";
import styles from "./page.module.css";

/** The design's wording for "no availability stated". */
const NO_TIMELINE = "No strict timeline";

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
    if (!skills.trim()) found.required_skills = "List what the work involves.";
    if (!description.trim()) found.description = "Describe the work that needs doing.";
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
      <p className={`subtitle ${styles.subtitle}`}>Describe the work you need done.</p>

      <div className="card">
        {errors.form && (
          <FormAlert className={styles.alert} message={errors.form} onRetry={retryable ? () => void submit() : undefined} busy={busy} />
        )}

        <form onSubmit={submit} noValidate>
          <TextInput
            label="Job title"
            required
            value={title}
            onChange={setTitle}
            error={errors.title}
            maxLength={255}
            placeholder="e.g. Electrician needed for 3-bedroom house wiring"
          />

          <TextArea
            label="What skills does this job need?"
            required
            value={skills}
            onChange={setSkills}
            error={errors.required_skills}
            rows={3}
            placeholder="e.g. Conduit bending, three-phase distribution board installation, earthing, trunking"
            hint="List what the work involves. Local terms are understood."
            hintIcon={
              <span aria-hidden="true" className={styles.hintIcon}>
                文
              </span>
            }
          />

          <TextArea
            label="Description"
            required
            value={description}
            onChange={setDescription}
            error={errors.description}
            rows={4}
            maxLength={4000}
            placeholder="Provide context on site readiness, materials on-site, access hours, and specific structural requirements..."
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
              label="When is it needed?"
              value={availability}
              onChange={setAvailability}
              options={AVAILABILITY}
              placeholder={NO_TIMELINE}
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
