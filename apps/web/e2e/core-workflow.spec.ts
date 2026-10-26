/**
 * Both journeys through a real browser, in Chromium and WebKit (NFR-05):
 * a worker signs up, describes their work and reads an explained match; a
 * client signs up, posts a job and sees how it was understood.
 *
 * Needs the API running on 127.0.0.1:5000 with a seeded database. Accounts are
 * created as the tests run; clear them afterwards with
 * `python scripts/seed_database.py --reset`.
 */

import { expect, test, type Page } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000";
const PIN = "4821";

/** A fresh 9-digit Kenyan mobile number (7 + 8 digits), unique per run. */
function phone(): string {
  const unique = String(Date.now()).slice(-6) + String(Math.floor(Math.random() * 90) + 10);
  return `7${unique}`;
}

/**
 * The page a person can actually see.
 *
 * Next keeps a route mounted in a hidden Activity after navigating away, so it
 * can restore state on back navigation. Every label therefore exists twice once
 * a journey has passed through two forms, and an unscoped locator is ambiguous.
 */
function view(page: Page) {
  return page.locator("main:visible");
}

async function fillPin(page: Page, label: RegExp, pin: string) {
  for (const [index, digit] of [...pin].entries()) {
    await view(page)
      .getByLabel(new RegExp(`${label.source}, digit ${index + 1}`))
      .fill(digit);
  }
}

async function createAccount(page: Page, role: "worker" | "client"): Promise<string> {
  const number = phone();
  await page.goto("/create-account");
  await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();
  await page.getByRole("radio", { name: role === "worker" ? "I'm a worker" : "I'm a client" }).click();
  await view(page).getByLabel("Phone number").fill(number);
  await fillPin(page, /Create a 4-digit PIN/, PIN);
  await fillPin(page, /Confirm PIN/, PIN);
  await page.getByRole("button", { name: "Create account" }).click();
  return number;
}

test.beforeAll(async ({ request }) => {
  const health = await request.get(`${API}/health`);
  expect(health.ok(), `the API must be running at ${API}`).toBeTruthy();
  expect((await health.json()).ready, "the engine must have finished loading").toBeTruthy();
});

test("a worker signs up, describes their work, and reads an explained match", async ({ page }) => {
  await createAccount(page, "worker");

  await expect(page).toHaveURL(/\/worker\/profile$/);
  await expect(page.getByRole("heading", { name: "Create your worker profile" })).toBeVisible();
  // No name or contact field is asked for (DR-07).
  await expect(page.getByLabel(/full name/i)).toHaveCount(0);

  await page.getByLabel(/What work do you do\?/).fill("fundi wa umeme, wiring, solar installation");
  await page.getByLabel(/About you/).fill("Nina uzoefu wa miaka mitano. Domestic and commercial installations.");
  await page.getByLabel(/Where do you work\?/).selectOption("Nairobi - Kasarani");
  await page.getByLabel(/When can you work\?/).selectOption("Full-time");
  await page.getByLabel(/Your daily rate/).fill("2500");
  await page.getByRole("button", { name: "Create profile" }).click();

  await expect(page).toHaveURL(/\/worker\/matches$/);
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();

  const first = page.locator("article").first();
  await expect(first).toContainText("#1");
  await expect(first.getByText(/Match score \d+/)).toBeVisible();
  await expect(first.getByText(/Strong|Moderate|Weak/).first()).toBeVisible();

  await first.getByRole("link", { name: "Why this job?" }).click();
  await expect(page).toHaveURL(/\/worker\/matches\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Why this job suits you" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What lined up" })).toBeVisible();
  await expect(page.getByText(/That's part of electrical work/).first()).toBeVisible();

  await page.getByRole("button", { name: /See the technical detail/ }).click();
  await expect(page.getByText("Rule-based score", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Matched skills" })).toBeVisible();
  await expect(page.getByText(/Listed by you|Your own words|Inferred via/).first()).toBeVisible();
});

test("a worker who gives no rate is told it could not be checked, not scored zero", async ({ page }) => {
  await createAccount(page, "worker");
  await page.getByLabel(/What work do you do\?/).fill("fundi wa umeme");
  await page.getByLabel(/About you/).fill("Electrical work in Nyeri for five years.");
  await page.getByLabel(/Where do you work\?/).selectOption("Nyeri");
  await page.getByRole("button", { name: "Create profile" }).click();

  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
  await page.locator("article").first().getByRole("link", { name: "Why this job?" }).click();
  await expect(page.getByRole("heading", { name: "What we couldn't check" })).toBeVisible();
  await expect(page.getByText(/so we couldn't check|couldn't compare/).first()).toBeVisible();

  await page.getByRole("button", { name: /See the technical detail/ }).click();
  await expect(page.getByText("Not assessed").first()).toBeVisible();
});

test("a worker whose wording is outside the vocabulary is told so plainly", async ({ page }) => {
  await createAccount(page, "worker");
  // "fundi wa stima" is deliberately withheld from the knowledge graph.
  await page.getByLabel(/What work do you do\?/).fill("fundi wa stima");
  await page.getByLabel(/About you/).fill("Nafanya kazi ya stima.");
  await page.getByLabel(/Where do you work\?/).selectOption("Thika");
  await page.getByRole("button", { name: "Create profile" }).click();

  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "No strong matches yet" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Edit your profile" })).toBeVisible();
});

test("a client signs up, posts a job, and sees how it was understood", async ({ page }) => {
  await createAccount(page, "client");

  await expect(page).toHaveURL(/\/client\/post$/);
  await expect(page.getByRole("heading", { name: "Post a job" })).toBeVisible();
  // Category is not asked for: matching never reads it. A client has no profile either.
  await expect(page.getByLabel(/category/i)).toHaveCount(0);
  await expect(page.getByRole("link", { name: "My profile" })).toHaveCount(0);

  // "fundi bomba" is the accepted plumber alias in the frozen vocabulary, and the
  // two skills are real ESCO labels, so this posting does reach a trade. Note the
  // title is not read by matching: the description and required skills are.
  await page.getByLabel("Job title").fill("Fix bathroom leakage");
  await page.getByLabel(/What skills does this job need\?/).fill("replace faucets, plumbing tools");
  await page.getByLabel("Description").fill("Need a fundi bomba. Bathroom leaking at the joints, materials are on site.");
  await page.getByLabel(/Budget per day/).fill("2200");
  await page.getByLabel(/Where is the job\?/).selectOption("Nairobi - Kawangware");
  await page.getByRole("button", { name: /Post job/ }).click();

  await expect(page).toHaveURL(/\/client\/postings\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Your job has been posted." })).toBeVisible();
  await expect(page.getByText("Client verbatim input")).toBeVisible();
  await expect(page.getByText(/We matched this to the trade/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Workers in this trade" })).toBeVisible();
  await expect(page.getByText(/describe themselves as/)).toBeVisible();

  // The trade list carries no score and no ranking.
  const pool = page.getByRole("heading", { name: "Workers in this trade" }).locator("..");
  await expect(pool.getByText(/Match score|Strong|Moderate|Weak/)).toHaveCount(0);

  await page.getByRole("link", { name: /Post another job/ }).click();
  await expect(page).toHaveURL(/\/client\/post$/);
});

test("a client's postings are listed, and only their own", async ({ page }) => {
  await createAccount(page, "client");
  await page.getByLabel("Job title").fill("Rewire a small shop");
  await page.getByLabel(/What skills does this job need\?/).fill("install electricity sockets");
  await page.getByLabel("Description").fill("Small shop in Nyeri needs a fundi wa umeme for rewiring.");
  await page.getByLabel(/Budget per day/).fill("2600");
  await page.getByLabel(/Where is the job\?/).selectOption("Nyeri");
  await page.getByRole("button", { name: /Post job/ }).click();
  await expect(page.getByRole("heading", { name: "Your job has been posted." })).toBeVisible();

  await page.getByRole("link", { name: "My postings" }).click();
  await expect(page).toHaveURL(/\/client\/postings$/);
  await expect(view(page).getByRole("link", { name: /Rewire a small shop/ })).toBeVisible();
  await expect(view(page).getByText("electrician")).toBeVisible();
});

test("signing in returns a worker to their matches", async ({ page }) => {
  const number = await createAccount(page, "worker");
  await page.getByLabel(/What work do you do\?/).fill("fundi wa umeme");
  await page.getByLabel(/About you/).fill("Five years of electrical work.");
  await page.getByLabel(/Where do you work\?/).selectOption("Nyeri");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page).toHaveURL(/\/worker\/matches$/);

  await page.getByRole("button", { name: /Sign out/ }).click();
  await expect(page).toHaveURL(/\/$/);

  await view(page).getByLabel("Phone number").fill(number);
  await fillPin(page, /4-digit PIN/, PIN);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/worker\/matches$/);
});

test("the wrong PIN is refused, and the form says so", async ({ page }) => {
  const number = await createAccount(page, "client");
  await page.getByRole("button", { name: /Sign out/ }).click();

  await view(page).getByLabel("Phone number").fill(number);
  await fillPin(page, /4-digit PIN/, "0000");
  await page.getByRole("button", { name: "Continue" }).click();
  // Scoped: Next's route announcer is also role="alert".
  await expect(view(page).getByRole("alert")).toContainText(/not right/);
  await expect(page).toHaveURL(/\/$/);
});

test("no PIN is left behind in the page after signing up", async ({ page }) => {
  // Next keeps the create-account route mounted but hidden after navigating
  // away. Whatever is still in its state stays in the DOM for the rest of the
  // session, so the PIN has to be cleared before leaving (DR-07).
  await createAccount(page, "worker");
  await expect(page).toHaveURL(/\/worker\/profile$/);

  const retained = await page
    .locator('input[type="password"], input[type="tel"]')
    .evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value).filter(Boolean));
  expect(retained).toEqual([]);
});

test("a signed-out visitor is sent to sign in", async ({ page }) => {
  await page.goto("/worker/matches");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
});
