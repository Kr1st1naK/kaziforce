/**
 * The national part of a Kenyan mobile number, as it is typed under the +254 prefix.
 *
 * Kenya's mobile numbers are ten digits in local form — 07xx xxx xxx or 01xx xxx xxx —
 * and the leading 0 is dropped once +254 is written in front. So the field holds nine
 * digits beginning 7 or 1, and nothing else is accepted. (01 was opened to mobile
 * allocations alongside 07; both reach the same network operators.)
 */

export const PHONE_DIGITS = 9;
const FIRST_DIGITS = ["7", "1"];

/** Everything that is not a digit, removed, and no more digits than the plan allows. */
export function phoneDigits(value: string): string {
  return value.replace(/\D/g, "").slice(0, PHONE_DIGITS);
}

/** Blocks of three, the way the number is read aloud: 712345678 -> "712 345 678". */
export function formatPhone(value: string): string {
  return (phoneDigits(value).match(/\d{1,3}/g) ?? []).join(" ");
}

/** The complaint to show, or null when the number is one the plan allows. */
export function phoneError(value: string): string | null {
  const digits = phoneDigits(value);
  if (digits.length === 0) return "Enter your phone number.";
  if (!FIRST_DIGITS.includes(digits[0])) return "A Kenyan mobile number starts 7 or 1 after +254.";
  if (digits.length < PHONE_DIGITS) return `Enter all ${PHONE_DIGITS} digits after +254.`;
  return null;
}
