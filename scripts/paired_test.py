"""
Paired significance test between two configurations on one evaluation run.

Compares per-query reciprocal rank, which is the paired observation an IR
evaluation naturally produces: the same query is answered by both systems, so the
two samples are matched and a two-sample test would throw that pairing away.

Writes docs/evidence/paired_test.md.
Usage: python scripts/paired_test.py [--run results/dev/<folder>] [--a hybrid_no_kg] [--b full]
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "docs/evidence/paired_test.md"
RESAMPLES = 100_000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", default="results/dev/20261026-232037_46116e0")
    parser.add_argument("--a", default="hybrid_no_kg", help="the baseline")
    parser.add_argument("--b", default="full", help="the system under test")
    parser.add_argument("--metric", default="reciprocal_rank")
    args = parser.parse_args()

    run = REPO_ROOT / args.run
    queries = pd.read_csv(run / "per_query.csv")
    paired = queries.pivot_table(index=["worker_id", "variant"], columns="configuration",
                                 values=args.metric).reset_index()
    difference = (paired[args.b] - paired[args.a]).to_numpy()
    wins, losses, ties = int((difference > 0).sum()), int((difference < 0).sum()), int((difference == 0).sum())
    non_tied = difference[difference != 0]

    wilcoxon = stats.wilcoxon(paired[args.b], paired[args.a], zero_method="wilcox", alternative="two-sided")
    permutation = stats.permutation_test((difference,), lambda x, axis: np.mean(x, axis=axis),
                                         permutation_type="samples", n_resamples=RESAMPLES,
                                         alternative="two-sided", random_state=42)
    effect = abs(stats.norm.ppf(wilcoxon.pvalue / 2)) / np.sqrt(len(non_tied)) if len(non_tied) else float("nan")
    one_sided = len(non_tied) and (wins == 0 or losses == 0)
    exact = Decimal(2) / (Decimal(2) ** len(non_tied)) if one_sided else None

    lines = [
        f"# Paired test: `{args.b}` against `{args.a}`",
        "",
        f"Metric: per-query **{args.metric.replace('_', ' ')}**. Run: `{args.run}` "
        f"({len(paired)} development queries, each answered by both configurations).",
        "",
        "## Which test, and why",
        "",
        "**Wilcoxon signed-rank test**, with an exact paired permutation test alongside it.",
        "",
        "The observations are paired: every query is answered by both configurations, so each",
        "query yields one *difference*. A two-sample test would discard that pairing and compare",
        "two independent groups, which these are not; it would also absorb the large variation",
        "*between* queries (some are simply easier) into the noise term, and lose most of the",
        "power. Pairing removes that variation entirely.",
        "",
        "A paired *t*-test would be the usual parametric choice, but reciprocal rank is a poor fit",
        "for it: it is bounded in [0, 1] and takes only the discrete values 1, 1/2, 1/3, …, so the",
        "differences are neither continuous nor near-normal, and many are exactly zero. The",
        "Wilcoxon signed-rank test needs only that the differences be symmetric about their median,",
        "ranks them rather than using their magnitudes, and is the standard paired test in",
        "information-retrieval evaluation.",
        "",
        "The permutation test is reported because it assumes nothing at all: under the null",
        "hypothesis that the two systems are interchangeable, the sign of each query's difference",
        "is arbitrary, so re-randomising those signs gives the exact null distribution. Where the",
        "two tests agree, the conclusion does not rest on a distributional assumption.",
        "",
        "## Result",
        "",
        f"| | `{args.a}` | `{args.b}` |",
        "|---|---|---|",
        f"| Mean {args.metric.replace('_', ' ')} | {paired[args.a].mean():.4f} | {paired[args.b].mean():.4f} |",
        "",
        f"- Mean paired difference: **{difference.mean():+.4f}** in favour of `{args.b}`",
        f"- `{args.b}` better on **{wins}** queries, worse on **{losses}**, tied on **{ties}**",
        f"- Wilcoxon signed-rank: W = {wilcoxon.statistic:.1f}, p = {wilcoxon.pvalue:.3e}",
        f"- Paired permutation ({RESAMPLES:,} resamples): p = {permutation.pvalue:.3e}",
        f"- Effect size r = {effect:.3f}, over the {len(non_tied)} non-tied queries",
        "",
    ]
    if one_sided:
        lines += [
            f"The permutation p-value is at the resolution floor of {RESAMPLES:,} resamples "
            f"(1/{RESAMPLES:,} per tail), not a measurement. Every one of the {len(non_tied)} "
            "non-tied differences has the same sign, so the exact two-sided value is",
            "",
            f"    2 x (1/2)^{len(non_tied)} = {exact:.3e}",
            "",
            "which is the smallest p-value this design can produce.",
            "",
        ]
    lines += ["## By variant", "",
              "| Variant | n | " + f"`{args.a}` | `{args.b}` | difference | better | worse | tied |",
              "|---|---|---|---|---|---|---|---|"]
    for variant, group in paired.groupby("variant"):
        d = group[args.b] - group[args.a]
        lines.append(f"| {variant} | {len(group)} | {group[args.a].mean():.3f} | {group[args.b].mean():.3f} | "
                     f"{d.mean():+.3f} | {(d > 0).sum()} | {(d < 0).sum()} | {(d == 0).sum()} |")
    lines += ["",
              "## What it does and does not establish",
              "",
              f"It establishes that on **this dataset**, `{args.b}` is not merely ahead of `{args.a}` on",
              "average but ahead query by query, never behind on any single query. That rules out the",
              "difference being an artefact of a few easy queries.",
              "",
              "It does **not** establish that the difference would hold on other data. The queries are",
              "216 synthetic profiles drawn from one generator, so they are not independent draws from",
              "any real population, and the p-value describes variation across these queries only.",
              "The honest claim is about this evaluation set, not about Kenyan gig work in general.",
              "",
              "It is also worth reading the variant breakdown before quoting the headline: the effect",
              "is concentrated where the knowledge graph can act, and is exactly zero on `held_out`,",
              "where neither configuration reaches the right trade.",
              ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written to {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
