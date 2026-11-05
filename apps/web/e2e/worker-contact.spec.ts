/**
 * A worker gives a name and agrees at sign-up; a client who posts a job in their trade sees the name on
 * a card, opens the worker's page and finds a number to ring; and the worker can take it all back.
 * Chromium and WebKit (NFR-05).
 *
 * The worker who signs up through the browser has a random worker_id, and a trade's list shows only
 * five workers chosen by that id, so they are rarely among them. The client therefore opens one of the
 * three demo plumbers (e2e/demo.ts), who are placed first. The worker who signs up is checked on their
 * own screens, and the demo worker is the one who withdraws and returns.
 */

import { expect, test, type Browser, type Page } from "@playwright/test";
import { DEMO_PIN, DEMO_WORKERS, seedDemoWorkers } from "./demo";

const PIN = "4821";
const [AMINA] = DEMO_WORKERS;

test.describe.configure({ mode: "serial" });

function phone(): string {
  return `7${String(Date.now()).slice(-6)}${Math.floor(Math.random() * 90) + 10}`;
}

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

/**
 * Fills the phone number and checks it stuck. A field filled before the page has hydrated is reset when
 * React takes over, and the dev server is slowest on the first visit; retrying until the number is
 * still there afterwards removes the race without sleeping.
 */
async function fillPhone(page: Page, number: string) {
  const field = view(page).getByLabel("Phone number", { exact: true });
  const shown = `${number.slice(0, 3)} ${number.slice(3, 6)} ${number.slice(6)}`;
  await expect(async () => {
    await field.fill(number);
    await expect(field).toHaveValue(shown, { timeout: 1000 });
  }).toPass();
}

async function signIn(page: Page, number: string, pin: string) {
  await page.goto("/sign-in");
  await fillPhone(page, number);
  await fillPin(page, /4-digit PIN/, pin);
  await page.getByRole("button", { name: "Continue" }).click();
}

async function newClient(browser: Browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto("/create-account");
  await page.getByRole("radio", { name: "I'm a client" }).click();
  await fillPhone(page, phone());
  await fillPin(page, /Create a 4-digit PIN/, PIN);
  await fillPin(page, /Confirm PIN/, PIN);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/client\/post$/);
  return { context, page };
}

/** Posts the plumbing job and waits for the confirmation screen with its worker cards. */
async function postPlumbingJob(page: Page) {
  await view(page).getByLabel("Job title").fill("Fix bathroom leakage");
  await view(page).getByLabel(/What skills does this job need\?/).fill("replace faucets, plumbing tools");
  await view(page).getByLabel("Description").fill("Need a fundi bomba. Bathroom leaking at the joints.");
  await view(page).getByLabel(/Budget per day/).fill("2200");
  await view(page).getByLabel(/Where is the job\?/).selectOption("Nairobi - Kawangware");
  await view(page).getByRole("button", { name: /Post job/ }).click();
  await expect(view(page).getByRole("heading", { name: "Workers in this trade" })).toBeVisible();
}

test.beforeAll(async ({ request }) => {
  const health = await request.get(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000"}/health`);
  expect((await health.json()).ready, "the API must be running and ready").toBeTruthy();
  seedDemoWorkers();
});

test("a worker signs up with a name and agreement, and sees them on their profile", async ({ page }) => {
  const number = phone();
  await page.goto("/create-account");

  // Both names and the agreement are required, and the form says which is missing.
  await fillPhone(page, number);
  await fillPin(page, /Create a 4-digit PIN/, PIN);
  await fillPin(page, /Confirm PIN/, PIN);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(view(page).getByText("Enter your first name.")).toBeVisible();
  await expect(view(page).getByText("Enter your last name.")).toBeVisible();
  await expect(view(page).getByText(/Agree to continue/)).toBeVisible();
  await expect(page).toHaveURL(/\/create-account/);

  await view(page).getByLabel(/^First name/).fill("Zawadi");
  await view(page).getByLabel(/^Last name/).fill("Mutua");
  await view(page).getByRole("checkbox", { name: /can see my name and phone number/ }).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/worker\/profile$/);

  await view(page).getByLabel(/What work do you do\?/).fill("fundi bomba, replace faucets");
  await view(page).getByLabel(/About you/).fill("Nafanya kazi ya mabomba. Plumbing repairs in Thika.");
  await view(page).getByLabel(/Where do you work\?/).selectOption("Thika");
  await view(page).getByRole("button", { name: "Create profile" }).click();
  await expect(page).toHaveURL(/\/worker\/matches$/);

  await page.getByRole("link", { name: "My profile" }).click();
  await expect(view(page).getByText("Zawadi Mutua")).toBeVisible();
  await expect(view(page).getByText(/clients who post a job in your trade can see your name and your number/i)).toBeVisible();
  await expect(view(page).getByText(`+254 ${number.slice(0, 3)} ${number.slice(3, 6)} ${number.slice(6)}`)).toBeVisible();
});

test("a client opens a named worker from the confirmation screen and finds a number to ring", async ({ browser }) => {
  const { context, page } = await newClient(browser);
  await postPlumbingJob(page);

  // Named cards link to profiles; the others stay anonymous. Nothing is ranked or numbered.
  const cards = view(page).locator("article");
  await expect(cards.first()).toBeVisible();
  for (const demo of DEMO_WORKERS) {
    await expect(cards.getByRole("link", { name: `${demo.first} ${demo.last}` })).toBeVisible();
  }
  await expect(cards.filter({ hasNot: page.getByRole("link") }).first()).toBeVisible(); // an anonymous card remains
  await expect(view(page).getByText(/Match score|Strong|Moderate|Weak|#\d/)).toHaveCount(0);

  const job = page.url();
  await cards.getByRole("link", { name: "Amina Wanjiru" }).click();
  await expect(page).toHaveURL(/\/client\/workers\/[0-9a-f-]{36}\?posting=/);
  await expect(view(page).getByRole("heading", { name: "Amina Wanjiru" })).toBeVisible();
  await expect(view(page).getByText("plumber", { exact: true })).toBeVisible();
  await expect(view(page).getByText("Nairobi - Kasarani")).toBeVisible();
  await expect(view(page).getByText("Full-time")).toBeVisible();
  const call = view(page).getByRole("link", { name: /Call Amina Wanjiru/ });
  await expect(call).toHaveAttribute("href", AMINA.tel);
  await expect(call).toHaveText(AMINA.display);
  await expect(view(page).getByText(/Match score|Strong|Moderate|Weak|#\d/)).toHaveCount(0);

  await page.getByRole("link", { name: /Back to your job posting/ }).click();
  await expect(page).toHaveURL(job);
  await context.close();
});

test("a worker who withdraws disappears from the client's cards and page at once, and can come back", async ({
  browser,
}) => {
  const { context: clientContext, page: client } = await newClient(browser);
  await postPlumbingJob(client);
  await client.locator("article").getByRole("link", { name: "Amina Wanjiru" }).click();
  await expect(view(client).getByRole("heading", { name: "Amina Wanjiru" })).toBeVisible();
  const profileUrl = client.url();

  const workerContext = await browser.newContext();
  const worker = await workerContext.newPage();
  try {
    await signIn(worker, AMINA.phone, DEMO_PIN);
    await expect(worker).toHaveURL(/\/worker\/matches$/);
    await worker.getByRole("link", { name: "My profile" }).click();
    await worker.getByRole("button", { name: "Edit profile" }).click();
    const consent = worker.getByRole("checkbox", { name: /can see my name and phone number/ });
    await expect(consent).toBeChecked();
    await consent.uncheck();
    await worker.getByRole("button", { name: "Save changes" }).click();
    await expect(view(worker).getByText(/Your name and number are hidden from clients/)).toBeVisible();

    // The client's page is gone on the next load, and says so without saying why.
    await client.goto(profileUrl);
    await expect(view(client).getByRole("alert")).toContainText("not available");
    await expect(view(client).getByRole("link", { name: /Call/ })).toHaveCount(0);

    // And on the confirmation screen the card is anonymous: still there, no name, no link.
    await client.getByRole("link", { name: "My postings" }).click();
    await view(client).getByRole("link", { name: /Fix bathroom leakage/ }).click();
    await expect(view(client).getByRole("heading", { name: "Workers in this trade" })).toBeVisible();
    await expect(view(client).getByRole("link", { name: "Amina Wanjiru" })).toHaveCount(0);
    await expect(view(client).locator("article")).toHaveCount(5);
  } finally {
    // Back on, however the test went, so the demo and the next run are as they were.
    seedDemoWorkers();
    await workerContext.close();
  }

  await client.goto(profileUrl);
  await expect(view(client).getByRole("heading", { name: "Amina Wanjiru" })).toBeVisible();
  await clientContext.close();
});

test("an unknown worker is simply not available", async ({ browser }) => {
  const { context, page } = await newClient(browser);
  await page.goto("/client/workers/00000000-0000-4000-8000-00000000dead");
  await expect(view(page).getByRole("alert")).toContainText("not available");
  await expect(view(page).getByRole("link", { name: /Back to my postings/ })).toBeVisible();
  await context.close();
});

test("a signed-out visitor cannot open a worker's page", async ({ page }) => {
  await page.goto("/client/workers/00000000-0000-4000-8000-00000000dead");
  await expect(page).toHaveURL(/\/sign-in$/);
});
