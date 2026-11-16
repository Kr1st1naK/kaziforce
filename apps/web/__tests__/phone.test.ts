/**
 * The phone field holds the national part of a Kenyan mobile number.
 *
 * Under the +254 prefix that is nine digits beginning 7 or 1 — the local 07xx/01xx
 * forms with their leading 0 dropped. These tests pin that rule down, because it is
 * the one thing on the account screen a wrong answer silently locks someone out of.
 */

import { describe, expect, it } from "vitest";
import { PHONE_DIGITS, formatPhone, phoneDigits, phoneError } from "@/lib/phone";

describe("phoneDigits", () => {
  it("keeps digits only and stops at the length of the national number", () => {
    expect(phoneDigits("712 345 678")).toBe("712345678");
    expect(phoneDigits("+254-712-345-678")).toBe("254712345");
    expect(phoneDigits("7123456789999")).toBe("712345678");
    expect(phoneDigits("712345678").length).toBe(PHONE_DIGITS);
  });
});

describe("formatPhone", () => {
  it("groups in threes as the number is typed", () => {
    expect(formatPhone("7")).toBe("7");
    expect(formatPhone("7123")).toBe("712 3");
    expect(formatPhone("712345678")).toBe("712 345 678");
  });

  it("does not leave a trailing separator on a complete block", () => {
    expect(formatPhone("712")).toBe("712");
    expect(formatPhone("712345")).toBe("712 345");
  });
});

describe("phoneError", () => {
  it("accepts the two mobile prefixes the numbering plan uses", () => {
    expect(phoneError("712345678")).toBeNull();
    expect(phoneError("110345678")).toBeNull();
    expect(phoneError("790 123 456")).toBeNull();
  });

  it("rejects a first digit that is not 7 or 1", () => {
    for (const first of ["0", "2", "3", "4", "5", "6", "8", "9"]) {
      expect(phoneError(`${first}12345678`)).toMatch(/starts 7 or 1/);
    }
  });

  it("rejects a number that is short, and asks for nothing when the field is empty", () => {
    expect(phoneError("71234567")).toMatch(/all 9 digits/);
    expect(phoneError("")).toBe("Enter your phone number.");
  });
});
