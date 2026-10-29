/**
 * NFR-01, measured where the requirement asks: in the browser, from the request
 * for the matches screen to the ranked list being on screen.
 *
 * The engine's own time is recorded alongside it, read from the `timing_ms` the
 * API reports on the same responses, so the two can be quoted separately. The
 * difference is everything the requirement includes and the engine figure does
 * not: HTTP, the session check, React rendering and paint.
 *
 * Writes docs/evidence/nfr01_browser_timing/<browser>.json.
 */

import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:5000";
const PIN = "4821";
const BUDGET_MS = 5000; // NFR-01
const WARMUP = 3;       // discarded: the dev server compiles a route on first request
const SAMPLES = 10;
const OUT = path.resolve(__dirname, "../../../docs/evidence/nfr01_browser_timing");

function view(page: Page) {
  return page.locator("main:visible");
}

async function fillPin(page: Page, label: RegExp, pin: string) {
  for (const [index, digit] of [...pin].entries()) {
    await view(page).getByLabel(new RegExp(`${label.source}, digit ${index + 1}`)).fill(digit);
  }
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function percentile(values: number[], p: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
}

test("the matches screen is on the worker's screen within NFR-01's budget", async ({ page, browserName }) => {
  test.setTimeout(180_000);

  const health = await page.request.get(`${API}/health`);
  expect((await health.json()).ready, "the engine must have finished loading").toBeTruthy();

  // Setup, untimed: an account and a profile to be matched.
  const phone = `7${String(Date.now()).slice(-6)}${Math.floor(Math.random() * 90) + 10}`;
  await page.goto("/create-account");
  await page.getByRole("radio", { name: "I'm a worker" }).click();
  await view(page).getByLabel("Phone number").fill(phone);
  await fillPin(page, /Create a 4-digit PIN/, PIN);
  await fillPin(page, /Confirm PIN/, PIN);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/worker\/profile$/);
  await view(page).getByLabel(/What work do you do\?/).fill("fundi wa umeme, wiring, solar installation");
  await view(page).getByLabel(/About you/).fill("Nina uzoefu wa miaka mitano. Domestic and commercial work.");
  await view(page).getByLabel(/Where do you work\?/).selectOption("Nairobi - Kasarani");
  await view(page).getByLabel(/When can you work\?/).selectOption("Full-time");
  await view(page).getByLabel(/Your daily rate/).fill("2500");
  await view(page).getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();

  // The engine's own time, as the API reports it on each /recommend response.
  const engine: number[] = [];
  page.on("response", async (response) => {
    if (!response.url().includes("/recommend")) return;
    try {
      const body = await response.json();
      if (typeof body.timing_ms === "number") engine.push(body.timing_ms);
    } catch {
      /* not a JSON body we can read */
    }
  });

  const browser: number[] = [];
  for (let i = 0; i < WARMUP + SAMPLES; i += 1) {
    await page.goto("/worker/profile"); // leave the route, so it is genuinely re-requested
    const started = Date.now();
    await page.goto("/worker/matches");
    await expect(page.locator("article").first()).toContainText("#1");
    const elapsed = Date.now() - started;
    if (i >= WARMUP) browser.push(elapsed);
  }

  const measured = engine.slice(-SAMPLES);
  const summary = {
    browser: browserName,
    samples: SAMPLES,
    warmup_discarded: WARMUP,
    budget_ms: BUDGET_MS,
    note: "Next.js development server; a production build would be faster.",
    end_to_end_ms: { median: median(browser), p95: percentile(browser, 0.95), max: Math.max(...browser) },
    engine_ms: measured.length
      ? { median: median(measured), p95: percentile(measured, 0.95), max: Math.max(...measured) }
      : null,
    end_to_end_samples_ms: browser,
  };

  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, `${browserName}.json`), `${JSON.stringify(summary, null, 2)}\n`);
  console.log(`[NFR-01] ${browserName}: end-to-end median ${summary.end_to_end_ms.median} ms, ` +
    `p95 ${summary.end_to_end_ms.p95} ms, max ${summary.end_to_end_ms.max} ms` +
    (summary.engine_ms ? ` | engine median ${summary.engine_ms.median} ms` : ""));

  expect(summary.end_to_end_ms.max, `every sample must be inside NFR-01's ${BUDGET_MS} ms`).toBeLessThan(BUDGET_MS);
});
