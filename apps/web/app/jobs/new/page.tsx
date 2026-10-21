"use client";

/**
 * Screen 02: post a job (FR-02, wireframe 02).
 *
 * No category field: the schema has the column, but matching never reads it,
 * so asking for one would imply it affects the result.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AmountField, SelectField, TextField } from "@/components/Field";
import { SkillsInput } from "@/components/SkillsInput";
import { useEngineStatus } from "@/components/EngineStatus";
import { ApiError, api } from "@/lib/api";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability, type JobInput } from "@/lib/types";

const MAX_TITLE = 255;
const MAX_DESCRIPTION = 4000;

export default function Page() {
  const router = useRouter();
  const { ready } = useEngineStatus();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [availability, setAvailability] = useState("");
  const [budget, setBudget] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!title.trim()) found.title = "Give the job a short title.";
    if (!description.trim()) found.description = "Describe the work that needs doing.";
    if (budget && Number(budget) < 0) found.budget = "A budget cannot be negative.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const posting: JobInput = {
      title: title.trim(),
      description: description.trim(),
      required_skills: requiredSkills,
      location: location.trim() || null,
      availability: (availability as Availability) || null,
      budget: budget === "" ? null : Number(budget),
    };
    setSubmitting(true);
    try {
      const created = await api.createJob(posting);
      router.push(`/jobs/${created.posting_id}`);
    } catch (error) {
      setSubmitting(false);
      setErrors(
        error instanceof ApiError
          ? { [error.field ?? "form"]: error.message }
          : { form: "Something went wrong. Please try again." },
      );
    }
  };

  return (
    <div className="panel">
      <h1>Post a job</h1>
      <p className="note">
        Describe the work in your own words. We will show you how the system understood it, and how many registered
        workers match.
      </p>

      {errors.form && (
        <div className="alert" role="alert">
          {errors.form}
        </div>
      )}

      <form onSubmit={submit} noValidate>
        <TextField
          label="Job title"
          value={title}
          onChange={setTitle}
          error={errors.title}
          hint="For example: House wiring for a new flat."
          maxLength={MAX_TITLE}
          disabled={submitting}
        />

        <TextField
          label="Description"
          value={description}
          onChange={setDescription}
          error={errors.description}
          hint="What needs doing, and anything a worker should know."
          maxLength={MAX_DESCRIPTION}
          multiline
          disabled={submitting}
        />

        <SkillsInput
          label="Required skills"
          skills={requiredSkills}
          onChange={setRequiredSkills}
          error={errors.required_skills}
          placeholder="install electricity sockets"
          hint="Only the skills you list here are used for matching. Press Enter or type a comma to add one."
          disabled={submitting}
        />

        <TextField
          label="Location"
          value={location}
          onChange={setLocation}
          error={errors.location}
          hint={`Any place. For example: ${SUGGESTED_LOCATIONS[0]}, ${SUGGESTED_LOCATIONS[17]}.`}
          maxLength={200}
          optional
          disabled={submitting}
        />

        <SelectField
          label="Availability needed"
          value={availability}
          onChange={setAvailability}
          options={AVAILABILITY}
          placeholder="Not stated"
          error={errors.availability}
          optional
          disabled={submitting}
        />

        <AmountField
          label="Budget"
          value={budget}
          onChange={setBudget}
          error={errors.budget}
          hint="What you can pay per day. Leave it blank if it is open."
          optional
          disabled={submitting}
        />

        <div className="actions">
          <button className="button button-primary" type="submit" disabled={submitting}>
            {submitting ? (ready ? "Posting…" : "Waiting for the engine…") : "Post job"}
          </button>
        </div>
      </form>
    </div>
  );
}
