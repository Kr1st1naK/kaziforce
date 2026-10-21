/**
 * The whole flow through a real browser, in Chromium and WebKit (NFR-05):
 * submit a profile, read the ranked jobs, open an explanation, post a job and
 * read its interpretation.
 *
 * Needs the API running on 127.0.0.1:5000 with a seeded database.
 */

import { expect, test } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000";

test.beforeAll(async ({ request }) => {
  const health = await request.get(`${API}/health`);
  expect(health.ok(), `the API must be running at ${API}`).toBeTruthy();
  const body = await health.json();
  expect(body.ready, "the engine must have finished loading").toBeTruthy();
});

test("a worker submits a profile and gets explained matches", async ({ page }) => {
  await page.goto("/worker");
  await expect(page.getByRole("heading", { name: "Create your worker profile" })).toBeVisible();

  // No name or contact field is asked for (DR-07).
  await expect(page.getByLabel(/full name/i)).toHaveCount(0);

  await page.getByLabel("About your work").fill("Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri.");
  await page.getByLabel(/^Skills/).fill("fundi wa umeme");
  await page.getByLabel(/^Skills/).press("Enter");
  await expect(page.getByRole("button", { name: "Remove fundi wa umeme" })).toBeVisible();
  await page.getByLabel(/^Location/).fill("Nyeri");
  await page.getByLabel(/^Availability/).selectOption("Part-time");
  await page.getByLabel(/^Daily rate/).fill("2000");
  await page.getByRole("button", { name: "Find jobs for me" }).click();

  await expect(page).toHaveURL(/\/worker\/[0-9a-f-]+\/matches$/);
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();

  // The knowledge graph mapped the informal term to its ESCO occupation.
  await expect(page.getByText(/Understood as electrician/)).toBeVisible();

  const firstMatch = page.locator("article").first();
  await expect(firstMatch).toContainText("#1");
  await expect(firstMatch.getByText(/inferred via fundi wa umeme/).first()).toBeVisible();

  await firstMatch.getByRole("link", { name: "Why this match?" }).click();
  await expect(page).toHaveURL(/\/matches\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Why this match?" })).toBeVisible();
  await expect(page.getByText("Rule-based score", { exact: true })).toBeVisible();
  await expect(page.getByText("Semantic score", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Matched skills/ })).toBeVisible();
  await expect(page.getByText("maps to").first()).toBeVisible();
});

test("an unrecognised term is reported, not silently dropped (FR-10)", async ({ page }) => {
  await page.goto("/worker");
  await page.getByLabel("About your work").fill("Mimi ni fundi wa stima, niko Thika.");
  await page.getByLabel(/^Skills/).fill("fundi wa stima");
  await page.getByLabel(/^Skills/).press("Enter");
  await page.getByRole("button", { name: "Find jobs for me" }).click();

  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
  await expect(page.getByText(/Not recognised/)).toBeVisible();
  await expect(page.getByText(/“fundi wa stima”/)).toBeVisible();
});

test("a criterion with no information reads as not assessed, never as zero", async ({ page }) => {
  await page.goto("/worker");
  // No location, availability or rate: three of the four criteria cannot be assessed.
  await page.getByLabel("About your work").fill("Mimi ni fundi wa umeme.");
  await page.getByLabel(/^Skills/).fill("fundi wa umeme");
  await page.getByLabel(/^Skills/).press("Enter");
  await page.getByRole("button", { name: "Find jobs for me" }).click();
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();

  await page.locator("article").first().getByRole("link", { name: "Why this match?" }).click();
  await expect(page.getByRole("heading", { name: /How each criterion scored/ })).toBeVisible();
  const notAssessed = page.getByText("Not assessed", { exact: true });
  expect(await notAssessed.count()).toBeGreaterThan(0);
  await expect(page.getByText(/It does not count for or against this match/).first()).toBeVisible();
});

test("a client posts a job and sees how it was understood", async ({ page }) => {
  await page.goto("/jobs/new");
  await expect(page.getByRole("heading", { name: "Post a job" })).toBeVisible();

  // Category is not asked for: matching never reads it.
  await expect(page.getByLabel(/category/i)).toHaveCount(0);

  await page.getByLabel("Job title").fill("Rewire a small shop in Nyeri");
  await page.getByLabel("Description").fill("We need an electrician in Nyeri to rewire a small shop.");
  await page.getByLabel(/^Required skills/).fill("install electricity sockets");
  await page.getByLabel(/^Required skills/).press("Enter");
  await page.getByLabel(/^Location/).fill("Nyeri");
  await page.getByLabel(/^Budget/).fill("2600");
  await page.getByRole("button", { name: "Post job" }).click();

  await expect(page).toHaveURL(/\/jobs\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Your job posting is live" })).toBeVisible();
  await expect(page.getByText(/Understood as electrician/)).toBeVisible();
  const statedSkills = page.getByRole("heading", { name: /Required skills you listed/ }).locator("..");
  await expect(statedSkills.getByText("install electricity sockets", { exact: true })).toBeVisible();
  await expect(statedSkills.getByText("recognised skill")).toBeVisible();
  await expect(page.getByText(/Matching uses these only/)).toBeVisible();
  await expect(page.getByText(/workers whose profiles match the electrician occupation/)).toBeVisible();

  // Refreshing works: the posting is read back from the database by its URL.
  await page.reload();
  await expect(page.getByText(/Understood as electrician/)).toBeVisible();
});

test("the form refuses an empty profile before it reaches the API", async ({ page }) => {
  await page.goto("/worker");
  await page.getByRole("button", { name: "Find jobs for me" }).click();
  await expect(page.getByText(/Tell us about your work/)).toBeVisible();
  await expect(page).toHaveURL(/\/worker$/);
});
