/**
 * A visitor arrives at the landing page, sees what the system does, and reaches create-account from either
 * entry point with the right role already chosen. Chromium and WebKit (NFR-05).
 *
 * Needs the web server only; no account is created, so nothing needs clearing afterwards.
 */

import { expect, test } from "@playwright/test";

test("the landing page explains the system and the trades it understands", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Work that fits your hands.");

  const trades = page.getByRole("list", { name: /Trades and the terms we know/ }).getByRole("listitem");
  await expect(trades).toHaveCount(11);
  await expect(trades.first()).toContainText("fundi wa umeme");
  await expect(trades.first()).toContainText("electrician");

  await expect(page.getByRole("region", { name: /How KaziForce works/ })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toHaveText("KaziForce © 2026");
  await expect(page.locator("img")).toHaveCount(0);
  await expect(page.getByRole("searchbox")).toHaveCount(0);
});

const ENTRIES = [
  ["the hero's I'm looking for work", "I'm looking for work", "I'm a worker"],
  ["the hero's I need a fundi", "I need a fundi", "I'm a client"],
  ["the worker panel", "Create a worker account", "I'm a worker"],
  ["the client panel", "Create a client account", "I'm a client"],
] as const;

for (const [where, entry, role] of ENTRIES) {
  test(`${where} reaches create-account as ${role}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: entry }).click();
    // A client-side navigation waits for the dev server to compile the route, which is slow when it is busy.
    await expect(page).toHaveURL(/\/create-account\?role=/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();
    await expect(page.getByRole("radio", { name: role })).toHaveAttribute("aria-checked", "true");
  });
}

test("Get started takes a visitor to the two entry cards", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Get started" }).click();
  await expect(page).toHaveURL(/#start$/);
  await expect(page.getByRole("heading", { name: "Looking for work?" })).toBeInViewport();
  await expect(page.getByRole("heading", { name: "Need a fundi?" })).toBeInViewport();
});

test("a returning visitor reaches sign-in from the top bar and from the foot", async ({ page }) => {
  for (const name of ["Sign in", "Sign in to your account"]) {
    await page.goto("/");
    await page.getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(/\/sign-in$/, { timeout: 45_000 });
    await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
  }
});

test("the keyboard reaches every way in, in reading order", async ({ page, browserName }) => {
  await page.goto("/");
  // Only links count: the first Tab can land on the page itself, whose text contains every label.
  const seen: string[] = [];
  for (let i = 0; i < 14; i++) {
    // Safari's Tab skips links unless a setting is on; Option+Tab is its way of moving through them.
    await page.keyboard.press(browserName === "webkit" ? "Alt+Tab" : "Tab");
    seen.push(
      await page.evaluate(() => {
        const focused = document.activeElement as HTMLElement | null;
        return focused?.tagName === "A" ? (focused.textContent ?? "").trim() : "";
      }),
    );
  }
  const first = (text: string) => seen.findIndex((entry) => entry.includes(text));
  expect(first("Sign in")).toBeGreaterThanOrEqual(0);
  expect(first("Get started")).toBeGreaterThan(first("Sign in"));
  expect(first("I'm looking for work")).toBeGreaterThan(first("Get started"));
  expect(first("I need a fundi")).toBeGreaterThan(first("I'm looking for work"));
});

test("at 375px wide nothing overflows and the cards stack", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const measured = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    const past = [...document.querySelectorAll("body *")]
      .filter((element) => {
        const box = element.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.right > width + 1 || box.left < -1);
      })
      .map((element) => `${element.tagName}.${String((element as HTMLElement).className).slice(0, 30)}`);
    return { scroll: document.documentElement.scrollWidth, width, past };
  });
  expect(measured.scroll).toBeLessThanOrEqual(measured.width);
  expect(measured.past).toEqual([]);

  // The two entry cards sit one above the other, not side by side.
  const looking = await page.getByRole("heading", { name: "Looking for work?" }).boundingBox();
  const need = await page.getByRole("heading", { name: "Need a fundi?" }).boundingBox();
  expect(need!.y).toBeGreaterThan(looking!.y + looking!.height);
});
