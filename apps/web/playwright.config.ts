/**
 * End-to-end tests in Chromium and WebKit, the engines behind Chrome and
 * Safari (NFR-05).
 *
 * These drive the real interface against the real API, so they are run by hand
 * and not in CI, which has neither a database nor the language model:
 *
 *     flask --app kaziforce_api.app run        # in the repository root
 *     npm run e2e                             # here; starts next dev itself
 *
 * A browser is needed once: npx playwright install chromium webkit
 */

import { defineConfig, devices } from "@playwright/test";

const WEB_PORT = 3000;
// 127.0.0.1, not localhost: the API runs on 127.0.0.1:5000 and the session cookie is
// SameSite=Lax, so the browser only sends it when both are the same host.
const WEB_HOST = "127.0.0.1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "e2e-report", open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 20_000 },
  use: { baseURL: `http://${WEB_HOST}:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: {
    command: `npx next dev --hostname ${WEB_HOST} --port ${WEB_PORT}`,
    url: `http://${WEB_HOST}:${WEB_PORT}`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
