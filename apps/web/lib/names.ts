/**
 * A first or last name, as the API accepts it: letters in any script, with single spaces,
 * hyphens, apostrophes or full stops between parts, and at most 60 characters.
 *
 * The API checks the same rule and is the one that counts; this only says so sooner.
 */

export const MAX_NAME = 60;
const NAME = /^\p{L}+(?:[ '’.-]\p{L}+)*\.?$/u;

/** Trimmed, with runs of spaces made single, the way the API will store it. */
export function tidyName(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

/** The complaint to show, or null when the name is acceptable. `what` is "first name" or "last name". */
export function nameError(value: string, what: string): string | null {
  const name = tidyName(value);
  if (!name) return `Enter your ${what}.`;
  if (name.length > MAX_NAME) return `Use ${MAX_NAME} characters or fewer.`;
  if (!NAME.test(name)) return "Use letters, spaces, hyphens and apostrophes only.";
  return null;
}
