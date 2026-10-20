/**
 * Captures each screen as a PNG for the thesis figures.
 *
 * Run on its own, after the API is up:  npm run e2e:screenshots
 * Files land in docs/evidence/screens/<browser>/.
 */

import { expect, test } from "@playwright/test";

const OUT = (browser: string, name: string) => `../../docs/evidence/screens/${browser}/${name}.png`;

test.describe.configure({ mode: "serial" });

test("capture the four screens", async ({ page, browserName }) => {
  await page.setViewportSize({ width: 1280, height: 900 });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Find work/ })).toBeVisible();
  await page.screenshot({ path: OUT(browserName, "00-landing"), fullPage: true });

  // 01: worker profile, filled in but not yet submitted
  await page.goto("/worker");
  await page.getByLabel("About your work").fill("Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri.");
  await page.getByLabel(/^Skills/).fill("fundi wa umeme");
  await page.getByLabel(/^Skills/).press("Enter");
  await page.getByLabel(/^Location/).fill("Nyeri");
  await page.getByLabel(/^Availability/).selectOption("Part-time");
  await page.getByLabel(/^Daily rate/).fill("2000");
  await page.screenshot({ path: OUT(browserName, "01-worker-profile"), fullPage: true });

  // 03: ranked matches
  await page.getByRole("button", { name: "Find jobs for me" }).click();
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
  await expect(page.locator("article").first()).toContainText("#1");
  await page.screenshot({ path: OUT(browserName, "03-recommendations"), fullPage: true });

  // 04: explanation
  await page.locator("article").first().getByRole("link", { name: "Why this match?" }).click();
  await expect(page.getByRole("heading", { name: /Matched skills/ })).toBeVisible();
  await page.screenshot({ path: OUT(browserName, "04-explanation"), fullPage: true });

  // 02: job posting, filled in but not yet submitted
  await page.goto("/jobs/new");
  await page.getByLabel("Job title").fill("Rewire a small shop in Nyeri");
  await page.getByLabel("Description").fill("We need an electrician in Nyeri to rewire a small shop.");
  await page.getByLabel(/^Required skills/).fill("install electricity sockets");
  await page.getByLabel(/^Required skills/).press("Enter");
  await page.getByLabel(/^Location/).fill("Nyeri");
  await page.getByLabel(/^Budget/).fill("2600");
  await page.screenshot({ path: OUT(browserName, "02-job-posting"), fullPage: true });

  // 05: how the posting was understood
  await page.getByRole("button", { name: "Post job" }).click();
  await expect(page.getByRole("heading", { name: "Your job posting is live" })).toBeVisible();
  await page.screenshot({ path: OUT(browserName, "05-posting-interpretation"), fullPage: true });
});
