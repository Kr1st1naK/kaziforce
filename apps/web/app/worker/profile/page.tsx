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
 * The profile holds no personally identifying information (DR-07). A worker's name and
 * whether clients may see it belong to the account, and are edited here only because this is
 * where a worker looks after how they appear. They are saved by the same PUT, and left out of
 * it when the account has no name yet.
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { AmountInput, Checkbox, Select, TextArea, TextInput } from "@/components/FormFields";
import { formatKes } from "@/components/MatchCard";
import { ApiErrorMessage, useGuard, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import { useIdleWhenHidden } from "@/lib/useIdleWhenHidden";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { MAX_NAME, nameError, tidyName } from "@/lib/names";
import { formatPhone } from "@/lib/phone";
import { AVAILABILITY, type Availability, type OwnContact, type Worker } from "@/lib/types";
import styles from "./page.module.css";

type Fields = {
  skills: string;
  biography: string;
  location: string;
  availability: string;
  rate: string;
  firstName: string;
  lastName: string;
  consent: boolean;
};

const EMPTY: Fields = {
  skills: "",
  biography: "",
  location: "",
  availability: "",
  rate: "",
  firstName: "",
  lastName: "",
  consent: false,
};

const CONSENT_LABEL = "Clients who post a job in my trade can see my name and phone number.";

function toFields(worker: Worker, contact: OwnContact | null): Fields {
  return {
    firstName: contact?.first_name ?? "",
    lastName: contact?.last_name ?? "",
    consent: contact?.consent ?? false,
    skills: worker.skills.join(", "),
    biography: worker.biography,
    location: worker.location ?? "",
    availability: worker.availability ?? "",
    rate: worker.rate_expectation === null ? "" : String(worker.rate_expectation),
  };
}

/** What the worker saved, laid out to be read rather than filled in. */
function ProfileView({ worker, contact, onEdit }: { worker: Worker; contact: OwnContact | null; onEdit: () => void }) {
  const name = contact?.first_name && contact.last_name ? `${contact.first_name} ${contact.last_name}` : null;
  return (
    <>
      <div className="card">
        <dl className={styles.details}>
          <div className={styles.detail}>
            <dt className={styles.term}>Your name</dt>
            <dd className={styles.value}>{name ?? <span className={styles.unset}>Not added yet</span>}</dd>
          </div>

          <div className={styles.detail}>
            <dt className={styles.term}>Shown to clients</dt>
            <dd className={styles.value}>
              {contact?.consent ? (
                `Yes: clients who post a job in your trade can see your name and your number, +254 ${formatPhone(contact.phone)}.`
              ) : (
                <span className={styles.unset}>No. Your name and number are hidden from clients.</span>
              )}
            </dd>
          </div>

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
  const [contact, setContact] = useState<OwnContact | null>(null);
  const [loaded, setLoaded] = useState(false);
  // null until the worker chooses: a profile that exists opens as something to read,
  // and one that does not opens as the form. Both are decided from the session, which
  // may still be arriving on the first render, so neither is captured as initial state.
  const [editing, setEditing] = useState<boolean | null>(null);
  const [fields, setFields] = useState<Fields>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  // Creating a profile leaves this page for the matches and stays mounted, hidden; clear busy so that it
  // does not say "Saving…" with nothing submitted when the worker comes back.
  useIdleWhenHidden(() => setBusy(false));
  const [confirming, setConfirming] = useState(false);

  const set = <K extends keyof Fields>(key: K) => (value: Fields[K]) => setFields((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    if (!existing) return;
    let cancelled = false;
    api
      .myProfile()
      .then(({ worker, contact: own }) => {
        if (cancelled) return;
        setSaved(worker);
        setContact(own);
        setFields(toFields(worker, own));
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

    // The name belongs to the account, not the profile. It is sent only when there is one to send:
    // an account from before names existed has none, and can save the rest of its profile without.
    const hasName = Boolean(fields.firstName.trim() || fields.lastName.trim());
    if (saved && (hasName || fields.consent)) {
      const badFirst = nameError(fields.firstName, "first name");
      const badLast = nameError(fields.lastName, "last name");
      if (badFirst) found.first_name = fields.consent && !hasName ? "Add your first and last name before sharing them." : badFirst;
      if (badLast) found.last_name = badLast;
    }
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
        const { worker, contact: own } = await api.updateMyProfile(
          hasName || fields.consent
            ? {
                ...input,
                first_name: tidyName(fields.firstName),
                last_name: tidyName(fields.lastName),
                contact_consent: fields.consent,
              }
            : input,
        );
        setSaved(worker);
        setContact(own);
        setFields(toFields(worker, own));
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
    setFields(saved ? toFields(saved, contact) : EMPTY);
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

      {!loading && saved && !showForm && <ProfileView worker={saved} contact={contact} onEdit={() => setEditing(true)} />}

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

            {saved && (
              <>
                <TextInput
                  label="First name"
                  value={fields.firstName}
                  onChange={set("firstName")}
                  error={errors.first_name}
                  maxLength={MAX_NAME}
                  disabled={busy}
                />
                <TextInput
                  label="Last name"
                  value={fields.lastName}
                  onChange={set("lastName")}
                  error={errors.last_name}
                  maxLength={MAX_NAME}
                  disabled={busy}
                />
                <Checkbox
                  label={CONSENT_LABEL}
                  checked={fields.consent}
                  onChange={set("consent")}
                  error={errors.contact_consent}
                  hint="Turn this off and clients can no longer see your name, your number or a link to your profile."
                  disabled={busy}
                />
              </>
            )}

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
