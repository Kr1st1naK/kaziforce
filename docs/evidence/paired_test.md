# Paired test: `full` against `hybrid_no_kg`

Metric: per-query **reciprocal rank**. Run: `results/dev/20261026-232037_46116e0` (216 development queries, each answered by both configurations).

## Which test, and why

**Wilcoxon signed-rank test**, with an exact paired permutation test alongside it.

The observations are paired: every query is answered by both configurations, so each
query yields one *difference*. A two-sample test would discard that pairing and compare
two independent groups, which these are not; it would also absorb the large variation
*between* queries (some are simply easier) into the noise term, and lose most of the
power. Pairing removes that variation entirely.

A paired *t*-test would be the usual parametric choice, but reciprocal rank is a poor fit
for it: it is bounded in [0, 1] and takes only the discrete values 1, 1/2, 1/3, …, so the
differences are neither continuous nor near-normal, and many are exactly zero. The
Wilcoxon signed-rank test needs only that the differences be symmetric about their median,
ranks them rather than using their magnitudes, and is the standard paired test in
information-retrieval evaluation.

The permutation test is reported because it assumes nothing at all: under the null
hypothesis that the two systems are interchangeable, the sign of each query's difference
is arbitrary, so re-randomising those signs gives the exact null distribution. Where the
two tests agree, the conclusion does not rest on a distributional assumption.

## Result

| | `hybrid_no_kg` | `full` |
|---|---|---|
| Mean reciprocal rank | 0.4972 | 0.9176 |

- Mean paired difference: **+0.4204** in favour of `full`
- `full` better on **111** queries, worse on **0**, tied on **105**
- Wilcoxon signed-rank: W = 0.0, p = 5.713e-20
- Paired permutation (100,000 resamples): p = 2.000e-05
- Effect size r = 0.868, over the 111 non-tied queries

The permutation p-value is at the resolution floor of 100,000 resamples (1/100,000 per tail), not a measurement. Every one of the 111 non-tied differences has the same sign, so the exact two-sided value is

    2 x (1/2)^111 = 7.704e-34

which is the smallest p-value this design can produce.

## By variant

| Variant | n | `hybrid_no_kg` | `full` | difference | better | worse | tied |
|---|---|---|---|---|---|---|---|
| formal | 64 | 0.984 | 1.000 | +0.016 | 2 | 0 | 62 |
| held_out | 24 | 0.321 | 0.321 | +0.000 | 0 | 0 | 24 |
| known_alias | 64 | 0.317 | 1.000 | +0.683 | 52 | 0 | 12 |
| minimal | 64 | 0.256 | 0.977 | +0.720 | 57 | 0 | 7 |

## What it does and does not establish

It establishes that on **this dataset**, `full` is not merely ahead of `hybrid_no_kg` on
average but ahead query by query, never behind on any single query. That rules out the
difference being an artefact of a few easy queries.

It does **not** establish that the difference would hold on other data. The queries are
216 synthetic profiles drawn from one generator, so they are not independent draws from
any real population, and the p-value describes variation across these queries only.
The honest claim is about this evaluation set, not about Kenyan gig work in general.

It is also worth reading the variant breakdown before quoting the headline: the effect
is concentrated where the knowledge graph can act, and is exactly zero on `held_out`,
where neither configuration reaches the right trade.
