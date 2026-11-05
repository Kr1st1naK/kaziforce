/**
 * A visitor arrives at the landing page and reaches create-account from either entry
 * point, with the right role already chosen. Chromium and WebKit (NFR-05).
 *
 * Needs the web server only; no account is created, so nothing needs clearing afterwards.
 */

import { expect, test } from "@playwright/test";

test("the landing page explains the system and offers two ways in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("list", { name: "An example" })).toContainText("fundi wa umeme");
  await expect(page.getByRole("list", { name: "An example" })).toContainText("Electrician");
  await expect(page.getByRole("region", { name: "How it works" })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("Strathmore University");
  await expect(page.locator("img")).toHaveCount(0);
});

for (const [entry, role] of [
  ["I'm looking for work", "I'm a worker"],
  ["I need a fundi", "I'm a client"],
] as const) {
  test(`"${entry}" reaches create-account as ${role}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: entry }).click();
    await expect(page).toHaveURL(/\/create-account\?role=/);
    await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();
    await expect(page.getByRole("radio", { name: role })).toHaveAttribute("aria-checked", "true");
  });
}

test("a returning visitor reaches sign-in from the landing page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
});
