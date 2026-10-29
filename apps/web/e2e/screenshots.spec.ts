/**
 * Captures each screen as a PNG for the thesis figures.
 *
 * The file names follow the approved designs in docs/UI views/, so a figure can
 * be set beside the design it was built from. The postings list has no design of
 * its own; it is composed from the confirmation row style, and is captured last.
 *
 * Run on its own, after the API is up:  npm run e2e:screenshots
 * Files land in docs/evidence/screens/<browser>/.
 */

import { expect, test, type Page } from "@playwright/test";

const OUT = (browser: string, name: string) => `../../docs/evidence/screens/${browser}/${name}.png`;
const PIN = "4821";

test.describe.configure({ mode: "serial" });

/** A fresh 9-digit Kenyan mobile number, unique per run. */
function phone(): string {
  return `7${String(Date.now()).slice(-6)}${Math.floor(Math.random() * 90) + 10}`;
}

/** Only the visible route: Next keeps the previous one mounted but hidden. */
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

/** Leaves the current account, if any: a signed-in visitor is redirected away. */
async function signOut(page: Page) {
  const button = page.locator("header:visible").getByRole("button", { name: /Sign out/ });
  if ((await button.count()) > 0) {
    await button.first().click();
    await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
  }
}

/** Fills the account form without submitting, so it can be photographed first. */
async function completeAccountForm(page: Page, role: "worker" | "client") {
  await signOut(page);
  await page.goto("/create-account");
  await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();
  await page.getByRole("radio", { name: role === "worker" ? "I'm a worker" : "I'm a client" }).click();
  await view(page).getByLabel("Phone number").fill(phone());
  await fillPin(page, /Create a 4-digit PIN/, PIN);
  await fillPin(page, /Confirm PIN/, PIN);
}

test.beforeAll(async ({ request }) => {
  const api = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000";
  const health = await request.get(`${api}/health`);
  expect(health.ok(), "the API must be running").toBeTruthy();
});

test("capture the eight screens", async ({ page, browserName }) => {
  const shot = (name: string) => page.screenshot({ path: OUT(browserName, name), fullPage: true });
  await page.setViewportSize({ width: 1280, height: 900 });

  // 01 sign_in
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
  await shot("01-sign_in");

  // 02 create_account, filled in but not yet submitted
  await completeAccountForm(page, "worker");
  await shot("02-create_account");
  await page.getByRole("button", { name: "Create account" }).click();

  // 03 create_worker_profile_view, filled in but not yet submitted
  await expect(page).toHaveURL(/\/worker\/profile$/);
  await view(page).getByLabel(/What work do you do\?/).fill("fundi wa umeme, wiring, solar installation");
  await view(page)
    .getByLabel(/About you/)
    .fill("Nina uzoefu wa miaka mitano. Domestic and commercial installations.");
  await view(page).getByLabel(/Where do you work\?/).selectOption("Nairobi - Kasarani");
  await view(page).getByLabel(/When can you work\?/).selectOption("Full-time");
  await view(page).getByLabel(/Your daily rate/).fill("2500");
  await shot("03-create_worker_profile_view");
  await view(page).getByRole("button", { name: "Create profile" }).click();

  // 04 job_matches_for_worker_view
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
  await expect(page.locator("article").first()).toContainText("#1");
  await shot("04-job_matches_for_worker_view");

  // 05 worker_explanation_view
  await page.locator("article").first().getByRole("link", { name: "Why this job?" }).click();
  await expect(page.getByRole("heading", { name: "Why this job suits you" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What lined up" })).toBeVisible();
  await shot("05-worker_explanation_view");

  // 06 no_matches: "fundi wa stima" is withheld from the knowledge graph, so a
  // worker who uses it has nothing above the display threshold.
  await completeAccountForm(page, "worker");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/worker\/profile$/);
  await view(page).getByLabel(/What work do you do\?/).fill("fundi wa stima");
  await view(page).getByLabel(/About you/).fill("Nafanya kazi ya stima.");
  await view(page).getByLabel(/Where do you work\?/).selectOption("Thika");
  await view(page).getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByRole("heading", { name: "No strong matches yet" })).toBeVisible();
  await shot("06-no_matches");

  // 07 job_posting_creation, filled in but not yet submitted
  await completeAccountForm(page, "client");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/client\/post$/);
  await view(page).getByLabel("Job title").fill("Fix bathroom leakage");
  await view(page).getByLabel(/What skills does this job need\?/).fill("replace faucets, plumbing tools");
  await view(page)
    .getByLabel("Description")
    .fill("Need a fundi bomba. Bathroom leaking at the joints, materials are on site.");
  await view(page).getByLabel(/Budget per day/).fill("2200");
  await view(page).getByLabel(/Where is the job\?/).selectOption("Nairobi - Kawangware");
  await shot("07-job_posting_creation");

  // 08 job_posted_confirmation
  await view(page).getByRole("button", { name: /Post job/ }).click();
  await expect(page.getByRole("heading", { name: "Your job has been posted." })).toBeVisible();
  await shot("08-job_posted_confirmation");

  // 09 the client's postings list, composed from the confirmation row style.
  await page.getByRole("link", { name: "My postings" }).click();
  await expect(page).toHaveURL(/\/client\/postings$/);
  await expect(view(page).getByRole("link", { name: /Fix bathroom leakage/ })).toBeVisible();
  await shot("09-client_postings_list");
});
