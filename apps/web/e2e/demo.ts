/**
 * The three demo plumbers (kaziforce_api/data/demo.py): named, consenting, and placed first in their
 * trade's list, so a client's confirmation screen reliably has named cards to open.
 *
 * A worker who signs up through the browser has a random worker_id and so is rarely among the five
 * shown for a trade; these are the ones a test can count on seeing.
 */

import { execFileSync } from "node:child_process";

export const DEMO_PIN = "4821";
export const DEMO_WORKERS = [
  { first: "Amina", last: "Wanjiru", phone: "700000001", display: "+254 700 000 001", tel: "tel:+254700000001" },
  { first: "Joseph", last: "Otieno", phone: "700000002", display: "+254 700 000 002", tel: "tel:+254700000002" },
  { first: "Grace", last: "Achieng", phone: "700000003", display: "+254 700 000 003", tel: "tel:+254700000003" },
] as const;

/** Creates the demo workers that are missing and makes sure they are consenting. Safe to repeat. */
export function seedDemoWorkers(): void {
  const python = process.env.E2E_PYTHON ?? "../../venv/bin/python";
  execFileSync(python, ["../../scripts/seed_demo_workers.py"], { stdio: "pipe", env: process.env });
}
