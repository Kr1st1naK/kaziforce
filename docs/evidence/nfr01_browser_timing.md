# NFR-01 measured end to end, in the browser

NFR-01 asks for top-K matches **returned to the frontend within 5 seconds, measured end to
end from request submission to result display**. The evaluation runner can only report the
engine's own time, so this is measured where the requirement puts it: in a real browser,
from the request for the matches screen to rank #1 being on screen.

Measured by `apps/web/e2e/performance.spec.ts` in both engines: 10 samples each,
after 3 discarded warm-up loads. The worker is the same throughout
(*fundi wa umeme*, Nairobi - Kasarani, full-time, KES 2,500), ranking all 280 postings.

## Result

| Browser | end-to-end median | p95 | max | engine median | p95 | max | browser overhead (median) |
|---|---|---|---|---|---|---|---|
| chromium | 594 | 1164 | 1164 | 18.7 | 41.0 | 41.0 | 575 |
| webkit | 598 | 700 | 700 | 13.7 | 16.5 | 16.5 | 584 |

All figures in milliseconds. **Budget: 5,000 ms. The slowest single sample in either engine
is 1164 ms**, so NFR-01 is met with a wide margin.

## Why both numbers are reported

The engine figure is what `results/dev/*/metrics.md` records: enrich the worker, score 280
postings, rank them. The end-to-end figure adds everything the requirement includes and that
one leaves out — the HTTP round trip, the session check the page makes first, React rendering,
and paint.

The gap is the point. End-to-end is roughly **thirty times** the engine time, so quoting the
engine figure alone against a requirement worded "end to end" would understate the real
latency by an order of magnitude, even though both are far inside the budget.

## Caveats

- **Next.js development server; a production build would be faster.** Route compilation is the reason warm-up samples are discarded; a
  production build would be faster, so this figure is conservative.
- Everything is on one machine over the loopback interface. A real deployment adds network
  latency between the browser and the API, which this does not measure.
- Startup is excluded, as it is in the engine figures: the model and the job embeddings load
  once per process, taking about 35 s, and are reported separately.
- The budget is checked against the slowest sample, not the median, so the assertion fails if
  any single load breaches it.

