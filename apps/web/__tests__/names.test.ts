import { describe, expect, it } from "vitest";
import { MAX_NAME, nameError, tidyName } from "@/lib/names";

describe("tidyName", () => {
  it("trims and makes runs of spaces single", () => {
    expect(tidyName("  Wanjiru   Njoroge ")).toBe("Wanjiru Njoroge");
  });
});

describe("nameError", () => {
  it.each(["Amina", "Mary-Anne", "O'Neil", "O’Neil", "Zoë", "Njoroge Wa Kamau", "Jr.", "A"])("accepts %s", (name) => {
    expect(nameError(name, "first name")).toBeNull();
  });

  it.each(["", "   "])("asks for a name when given %j", (name) => {
    expect(nameError(name, "first name")).toBe("Enter your first name.");
    expect(nameError(name, "last name")).toBe("Enter your last name.");
  });

  it.each(["A1", "<b>", "Amina;", "-", "'", "12", "Am_ina", "Amina--Wanjiru"])("refuses %s", (name) => {
    expect(nameError(name, "first name")).toBe("Use letters, spaces, hyphens and apostrophes only.");
  });

  it("allows exactly the limit and refuses one more", () => {
    expect(nameError("a".repeat(MAX_NAME), "first name")).toBeNull();
    expect(nameError("a".repeat(MAX_NAME + 1), "first name")).toBe(`Use ${MAX_NAME} characters or fewer.`);
  });
});
