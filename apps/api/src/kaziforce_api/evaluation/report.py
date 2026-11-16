"""Writes an evaluation run folder: metrics.csv, per_query.csv, run.json and a readable metrics.md."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from kaziforce_api.evaluation.evaluator import ALL, VARIANTS, RunResult
from kaziforce_api.evaluation.metrics import chance_precision_at_k, chance_reciprocal_rank

N_RELEVANT, N_CANDIDATES = 8, 280  # every worker has exactly 8 relevant postings among 280


def _table(header: list[str], rows: list[list]) -> list[str]:
    return [f"| {' | '.join(header)} |", "|" + "---|" * len(header)] + [f"| {' | '.join(map(str, r))} |" for r in rows]


def _f(x: float) -> str:
    return f"{x:.3f}"


def write_run(result: RunResult, metadata: dict, out_dir: Path, ablation_pairs=()) -> Path:
    out_dir.mkdir(parents=True, exist_ok=False)
    summary = result.summary()
    metric_cols = [f"P@{k}" for k in result.ks] + ["MRR"]

    with open(out_dir / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        w.writeheader()
        w.writerows({k: round(v, 6) if isinstance(v, float) else v for k, v in row.items()} for row in summary)
    with open(out_dir / "per_query.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["configuration", "worker_id", "variant", "first_relevant_rank", "reciprocal_rank",
                    *[f"P@{k}" for k in result.ks], "explained", "covered", "covered_inclusive", "covered_graph",
                    "query_ms"])
        for q in result.queries:
            w.writerow([q.configuration, q.worker_id, q.variant, q.first_relevant_rank or "", round(q.reciprocal_rank, 6),
                        *[round(q.precision[k], 6) for k in result.ks],
                        q.explained, q.covered, q.covered_inclusive, q.covered_graph, round(q.query_ms, 3)])
    (out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    cell = {(r["configuration"], r["variant"]): r for r in summary}
    variants = [v for v in VARIANTS if any((c, v) in cell for c in result.configurations)]
    chance_p, chance_rr = chance_precision_at_k(N_RELEVANT, N_CANDIDATES), chance_reciprocal_rank(N_RELEVANT, N_CANDIDATES)
    n_queries = cell[(result.configurations[0], ALL)]["queries"]
    lines = [f"# Evaluation run {out_dir.name}", "",
             f"Split: **{result.split}** ({n_queries} worker queries, each ranking all {N_CANDIDATES} postings; "
             f"{N_RELEVANT} relevant per worker). Commit `{metadata['git']['commit'][:7]}`"
             + (" **with uncommitted changes**" if metadata["git"]["uncommitted_changes"] else "")
             + f". Single deterministic run (seed {metadata['seed']}); no confidence intervals.", "",
             "## All variants", "",
             *_table(["Configuration", *metric_cols], [[c, *[_f(cell[(c, ALL)][m]) for m in metric_cols]]
                                                       for c in result.configurations]),
             f"| *random ranking (expected)* | {' | '.join([_f(chance_p)] * len(result.ks))} | {_f(chance_rr)} |", ""]
    for metric in ("MRR", f"P@{5 if 5 in result.ks else result.ks[0]}"):
        lines += [f"## {metric} by variant", "",
                  *_table(["Configuration", *variants, ALL],
                          [[c, *[_f(cell[(c, v)][metric]) if (c, v) in cell else "—" for v in (*variants, ALL)]]
                           for c in result.configurations]), ""]
    if ablation_pairs:
        lines += ["## Knowledge-graph effect (MRR, with KG minus without; same scorer, only the enricher differs)", "",
                  *_table(["Scorer", "Without KG → with KG", *variants, ALL],
                          [[b.removesuffix("_kg") if b != "full" else "hybrid", f"{a} → {b}",
                            *[f"{cell[(b, v)]['MRR'] - cell[(a, v)]['MRR']:+.3f}" for v in (*variants, ALL)]]
                           for a, b in ablation_pairs if (a, ALL) in cell and (b, ALL) in cell]), ""]
    if any(cell[(c, ALL)]["explained"] for c in result.configurations):
        target = "full" if "full" in result.configurations else result.configurations[-1]
        lines += ["## Explanation coverage (NFR-02)", "",
                  "Share of the top-10 results for which the generator can state at least one concrete, "
                  "attributable reason. Definition fixed in `docs/scoring-policy.md` §7 before the generator "
                  "was written. **Coverage** is the NFR-02 figure (a shared skill is required); the other two "
                  "columns are reported for comparison. Computed over the whole top-10, never only the "
                  "results above the display threshold.", "",
                  *_table(["Configuration", "Coverage (NFR-02)", "Inclusive", "Graph-traced"],
                          [[c, _f(cell[(c, ALL)]["coverage"]), _f(cell[(c, ALL)]["coverage_inclusive"]),
                            _f(cell[(c, ALL)]["coverage_graph"])] for c in result.configurations]), "",
                  f"NFR-02 is assessed against **{target}**, the deployed system: "
                  f"**{cell[(target, ALL)]['coverage']:.1%}** against a target of 85%. "
                  "`keyword`, `semantic_only` and `semantic_kg` have no rule component, so they produce no "
                  "matched skills and no assessed criteria; their coverage is 0 by construction, not by "
                  "failure.", "",
                  "### Coverage by variant (NFR-02 rule)", "",
                  *_table(["Configuration", *variants, ALL],
                          [[c, *[_f(cell[(c, v)]["coverage"]) if (c, v) in cell else "—" for v in (*variants, ALL)]]
                           for c in result.configurations]), ""]
    lines += ["## Response time per query (after startup)", "",
              f"Startup, once per run: {metadata['startup_seconds']:.1f} s (graph, job enrichment, model load and "
              "job embeddings). Per query: enrich the worker, score all postings, rank.", "",
              *_table(["Configuration", "median ms", "p95 ms", "max ms"],
                      [[c, f"{cell[(c, ALL)]['median_ms']:.0f}", f"{cell[(c, ALL)]['p95_ms']:.0f}",
                        f"{cell[(c, ALL)]['max_ms']:.0f}"] for c in result.configurations]), "",
              "Explanations are generated after the timer stops: they are evaluation output, not part of "
              "answering a query, so these timings stay comparable with runs recorded before coverage existed.", "",
              "## Notes", "",
              f"- P@10 cannot exceed {N_RELEVANT / 10:.1f}: each worker has {N_RELEVANT} relevant postings.",
              "- Ties are broken by one fixed random order of the postings (seed 42), the same for every configuration.",
              "- Relevance is same occupational area; location, budget and availability do not affect it "
              "(docs/scoring-policy.md).",
              f"- Machine: {metadata['machine']['platform']}, {metadata['machine']['processor']}, "
              f"Python {metadata['machine']['python']}.", ""]
    (out_dir / "metrics.md").write_text("\n".join(lines), encoding="utf-8")
    return out_dir
