"use client";

/**
 * Screen 01: create a worker profile (FR-01, wireframe 01).
 *
 * No name or contact field: profiles hold no personally identifying
 * information (DR-07). The same rules the API enforces are checked here first,
 * and a 400 from the API is shown against the field it names.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AmountField, SelectField, TextField } from "@/components/Field";
import { SkillsInput } from "@/components/SkillsInput";
import { useEngineStatus } from "@/components/EngineStatus";
import { ApiError, api } from "@/lib/api";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability, type WorkerInput } from "@/lib/types";
import styles from "./page.module.css";

const MAX_BIOGRAPHY = 4000;

export default function Page() {
  const router = useRouter();
  const { ready } = useEngineStatus();
  const [biography, setBiography] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [availability, setAvailability] = useState("");
  const [rate, setRate] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const validate = (): Record<string, string> => {
    const found: Record<string, string> = {};
    if (!biography.trim()) found["worker.biography"] = "Tell us about your work. This is the only required field.";
    if (rate && Number(rate) < 0) found["worker.rate_expectation"] = "A daily rate cannot be negative.";
    return found;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const profile: WorkerInput = {
      biography: biography.trim(),
      skills,
      location: location.trim() || null,
      availability: (availability as Availability) || null,
      rate_expectation: rate === "" ? null : Number(rate),
    };
    setSubmitting(true);
    try {
      const created = await api.createWorker(profile);
      router.push(`/worker/${created.worker_id}/matches`);
    } catch (error) {
      setSubmitting(false);
      if (error instanceof ApiError) {
        setErrors({ [error.field ?? "form"]: error.message });
      } else {
        setErrors({ form: "Something went wrong. Please try again." });
      }
    }
  };

  return (
    <div className="panel">
      <h1>Create your worker profile</h1>
      <p className="note">
        Describe your work in your own words, in English or Kiswahili. We do not ask for your name or phone number.
      </p>

      {errors.form && (
        <div className="alert" role="alert">
          {errors.form}
        </div>
      )}

      <form onSubmit={submit} noValidate>
        <TextField
          label="About your work"
          value={biography}
          onChange={setBiography}
          error={errors["worker.biography"]}
          hint="For example: Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri."
          maxLength={MAX_BIOGRAPHY}
          multiline
          disabled={submitting}
        />

        <SkillsInput
          label="Skills"
          skills={skills}
          onChange={setSkills}
          error={errors["worker.skills"]}
          placeholder="fundi wa umeme"
          disabled={submitting}
        />

        <TextField
          label="Location"
          value={location}
          onChange={setLocation}
          error={errors["worker.location"]}
          hint={`Any place. For example: ${SUGGESTED_LOCATIONS[0]}, ${SUGGESTED_LOCATIONS[17]}.`}
          maxLength={200}
          optional
          disabled={submitting}
        />

        <SelectField
          label="Availability"
          value={availability}
          onChange={setAvailability}
          options={AVAILABILITY}
          placeholder="Not stated"
          error={errors["worker.availability"]}
          optional
          disabled={submitting}
        />

        <AmountField
          label="Daily rate"
          value={rate}
          onChange={setRate}
          error={errors["worker.rate_expectation"]}
          hint="What you expect per day. Leave it blank if you would rather not say."
          optional
          disabled={submitting}
        />

        <div className="actions">
          <button className="button button-primary" type="submit" disabled={submitting}>
            {submitting ? (ready ? "Finding jobs…" : "Waiting for the engine…") : "Find jobs for me"}
          </button>
          <span className={styles.aside}>Nothing is published. Your profile is used to rank jobs for you.</span>
        </div>
      </form>
    </div>
  );
}
