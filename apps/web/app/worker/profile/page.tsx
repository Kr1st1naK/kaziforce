"use client";

/**
 * The worker's profile (FR-01), in two states.
 *
 * A worker who has no profile yet gets the form straight away, and submitting it
 * runs the matching and takes them to their matches. A worker who already has one
 * gets what they saved, laid out to be read, with an "Edit profile" button that
 * turns the same screen back into the form. Editing saves over the stored profile
 * (PUT /workers/me) and returns to the reading view; it does not create a second one.
 *
 * No name or contact field: profiles hold no personally identifying
 * information (DR-07).
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { AmountInput, Select, TextArea } from "@/components/FormFields";
import { formatKes } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability, type Worker } from "@/lib/types";
import styles from "./page.module.css";

type Fields = { skills: string; biography: string; location: string; availability: string; rate: string };

const EMPTY: Fields = { skills: "", biography: "", location: "", availability: "", rate: "" };

function toFields(worker: Worker): Fields {
  return {
    skills: worker.skills.join(", "),
    biography: worker.biography,
    location: worker.location ?? "",
    availability: worker.availability ?? "",
    rate: worker.rate_expectation === null ? "" : String(worker.rate_expectation),
  };
}

/** What the worker saved, laid out to be read rather than filled in. */
function ProfileView({ worker, onEdit }: { worker: Worker; onEdit: () => void }) {
  return (
    <>
      <div className="card">
        <dl className={styles.details}>
          <div className={styles.detail}>
            <dt className={styles.term}>What you do</dt>
            <dd className={styles.value}>
              {worker.skills.length > 0 ? (
                <ul className={styles.skills}>
                  {worker.skills.map((skill) => (
                    <li key={skill} className={styles.skill}>
                      {skill}
                    </li>
                  ))}
                </ul>
              ) : (
                <span className={styles.unset}>Not stated</span>
              )}
            </dd>
          </div>

          <div className={styles.detail}>
            <dt className={styles.term}>About you</dt>
            <dd className={styles.value}>{worker.biography}</dd>
          </div>

          <div className={styles.detail}>
            <dt className={styles.term}>Where you work</dt>
            <dd className={styles.value}>{worker.location ?? <span className={styles.unset}>Not stated</span>}</dd>
          </div>

          <div className={styles.detail}>
            <dt className={styles.term}>When you can work</dt>
            <dd className={styles.value}>{worker.availability ?? <span className={styles.unset}>Not stated</span>}</dd>
          </div>

          <div className={styles.detail}>
            <dt className={styles.term}>Your daily rate</dt>
            <dd className={styles.value}>
              {worker.rate_expectation === null ? (
                <span className={styles.unset}>Not stated</span>
              ) : (
                formatKes(worker.rate_expectation)
              )}
            </dd>
          </div>
        </dl>
      </div>

      <div className={styles.viewActions}>
        <button type="button" className="button" onClick={onEdit}>
          Edit profile
        </button>
      </div>
    </>
  );
}

export default function Page() {
  const waiting = useGuard("worker");
  const { session, refresh } = useSession();
  const router = useRouter();
  const existing = session?.worker_profile_id ?? null;

  const [saved, setSaved] = useState<Worker | null>(null);
  const [loaded, setLoaded] = useState(false);
  // null until the worker chooses: a profile that exists opens as something to read,
  // and one that does not opens as the form. Both are decided from the session, which
  // may still be arriving on the first render, so neither is captured as initial state.
  const [editing, setEditing] = useState<boolean | null>(null);
  const [fields, setFields] = useState<Fields>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const set = <K extends keyof Fields>(key: K) => (value: string) => setFields((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    if (!existing) return;
    let cancelled = false;
    api
      .myProfile()
      .then(({ worker }) => {
        if (cancelled) return;
        setSaved(worker);
        setFields(toFields(worker));
      })
      .catch((caught) => !cancelled && setErrors({ form: ApiErrorMessage(caught) }))
      .finally(() => !cancelled && setLoaded(true));
    return () => {
      cancelled = true;
    };
  }, [existing]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!fields.skills.trim()) found.skills = "Tell us what work you do.";
    if (!fields.biography.trim()) found.biography = "Add a short description of your work.";
    if (!fields.location) found.location = "Choose where you work.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const input = {
      biography: fields.biography.trim(),
      skills: fields.skills
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean),
      location: fields.location,
      availability: (fields.availability as Availability) || null,
      rate_expectation: fields.rate === "" ? null : Number(fields.rate),
    };

    setBusy(true);
    try {
      if (saved) {
        const { worker } = await api.updateMyProfile(input);
        setSaved(worker);
        setFields(toFields(worker));
        setErrors({});
        setEditing(false);
        setBusy(false);
      } else {
        await api.createWorker(input);
        await refresh();
        router.push("/worker/matches");
      }
    } catch (error) {
      setBusy(false);
      setErrors(
        error instanceof ApiError && error.field
          ? { [error.field.replace("worker.", "")]: error.message }
          : { form: ApiErrorMessage(error) },
      );
    }
  };

  /** Cancel on a new profile clears the form; on an edit it puts back what was saved. */
  const discard = () => {
    setFields(saved ? toFields(saved) : EMPTY);
    setErrors({});
    setConfirming(false);
    if (saved) setEditing(false);
  };

  if (waiting) return null;

  const loading = Boolean(existing) && !loaded;
  const showForm = editing ?? !existing;
  const heading = saved ? "My profile" : "Create your worker profile";
  const subtitle = saved
    ? "What clients are matched against. Keep it current and the matches follow."
    : "Tell us about your work. We'll find jobs that suit you.";

  return (
    <AppShell>
      <h1>{heading}</h1>
      <p className={`subtitle ${styles.subtitle}`}>{subtitle}</p>

      {errors.form && (
        <div className={`alert ${styles.alert}`} role="alert">
          {errors.form}
        </div>
      )}

      {loading && (
        <p className={styles.loading} role="status" aria-live="polite">
          Loading your profile…
        </p>
      )}

      {!loading && saved && !showForm && <ProfileView worker={saved} onEdit={() => setEditing(true)} />}

      {!loading && showForm && (
        <div className="card">
          <form onSubmit={submit} noValidate>
            <TextArea
              label="What work do you do?"
              required
              value={fields.skills}
              onChange={set("skills")}
              error={errors.skills}
              rows={3}
              maxLength={2000}
              hint="Use your own words, in English or Kiswahili. For example: fundi wa umeme, wiring, solar installation."
            />

            <TextArea
              label="About you"
              required
              value={fields.biography}
              onChange={set("biography")}
              error={errors.biography}
              rows={3}
              maxLength={4000}
              hint="A short description of your work and how long you've been doing it."
            />

            <Select
              label="Where do you work?"
              required
              value={fields.location}
              onChange={set("location")}
              options={SUGGESTED_LOCATIONS}
              placeholder="Select location"
              error={errors.location}
            />

            <Select
              label="When can you work?"
              value={fields.availability}
              onChange={set("availability")}
              options={AVAILABILITY}
              placeholder="Select availability"
              error={errors.availability}
            />

            <AmountInput
              label="Your daily rate"
              value={fields.rate}
              onChange={set("rate")}
              placeholder="e.g. 2500"
              error={errors.rate_expectation}
              hint="Adding this helps us find better matches."
            />

            <div className={styles.actions}>
              <button type="button" className="link" onClick={() => setConfirming(true)} disabled={busy}>
                Cancel
              </button>
              <button className="button" type="submit" disabled={busy}>
                {saved ? (busy ? "Saving…" : "Save changes") : busy ? "Finding your matches…" : "Create profile"}
              </button>
            </div>
          </form>
        </div>
      )}

      {confirming && (
        <ConfirmDialog
          question={saved ? "Discard your changes?" : "Clear this form?"}
          detail={
            saved
              ? "Your profile goes back to what you last saved. Anything you have typed since is lost."
              : "Everything you have typed will be removed and you can start again."
          }
          confirmLabel={saved ? "Yes, discard them" : "Yes, clear it"}
          cancelLabel={saved ? "No, keep editing" : "No, keep it"}
          onConfirm={discard}
          onCancel={() => setConfirming(false)}
        />
      )}
    </AppShell>
  );
}
