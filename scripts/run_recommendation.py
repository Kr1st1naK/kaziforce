"""
End-to-end recommendation for one worker (the Sprint II core workflow).

Input: a worker profile from the development split. Processing: knowledge
graph enrichment, rule-based and semantic scoring of all 280 job postings,
hybrid combination. Output: the top K jobs with the composite score, both
components, the rule breakdown and the matched skills with how the worker came
to have each one.

Startup (graph, job enrichment, model, job embeddings) is timed separately from
the query, which is the per-query response time (NFR-01).

Usage:
    python scripts/run_recommendation.py --list 10
    python scripts/run_recommendation.py --worker-id <id> [--k 10] [--config full]
"""

from __future__ import annotations

import argparse
import time

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.matching.semantic import SemanticScorer, job_text
from kaziforce_api.pipeline import CONFIGURATIONS, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import INFORMAL_TERM, LISTED, OCCUPATION_LABEL, TEXT

SPLIT = "development"


def provenance(m, kg_label) -> str:
    if m.source == INFORMAL_TERM:
        return f"inferred via {kg_label(m.graph_path[0][0])}"
    if m.source == OCCUPATION_LABEL:
        return f"inferred via occupation {kg_label(m.graph_path[0][0])}"
    return {LISTED: "listed", TEXT: "your own words"}.get(m.source, m.source)


def fmt(value, spec=".3f") -> str:
    return "—" if value is None else format(value, spec)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--worker-id", help="a development-split worker ID (see --list)")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--config", default="full", choices=list(CONFIGURATIONS))
    parser.add_argument("--list", type=int, metavar="N", help="list N development-split workers and exit")
    args = parser.parse_args()

    loader = DataLoader()
    if args.list:
        for w in loader.workers(SPLIT)[: args.list]:
            print(f"{w.worker_id}  {w.biography[:70]}")
        return
    if not args.worker_id:
        parser.error("--worker-id is required (or use --list)")
    worker = loader.worker(args.worker_id, SPLIT)

    t0 = time.perf_counter()
    jobs = loader.jobs()
    kg = KnowledgeGraphBuilder().build()
    semantic = SemanticScorer()
    recommender = build_recommender(args.config, jobs, kg=kg, semantic=semantic, k=args.k)
    t_build = time.perf_counter()
    if args.config in ("semantic_only", "hybrid_no_kg", "full"):
        semantic.embed([job_text(j) for j in recommender.jobs])  # model load + job embeddings, once per process
    t_startup = time.perf_counter()
    results = recommender.rank(worker)
    t_query = time.perf_counter()

    by_id = {j.profile.posting_id: j.profile for j in recommender.jobs}
    enrichment = recommender.enrich(worker).enrichment
    print(f"Configuration: {args.config}   Split: {SPLIT}   Candidate jobs: {len(jobs)}")
    print(f"\nWORKER {worker.worker_id}\n  bio:      {worker.biography}\n  skills:   {', '.join(worker.skills)}")
    print(f"  location: {worker.location or '—'}   availability: {worker.availability or '—'}   "
          f"rate: {fmt(worker.rate_expectation, '.0f')} KES/day")
    print(f"  enrichment: occupations {[kg.label(o) for o in enrichment.occupations] or 'none'}; "
          f"{len(enrichment.stated_skills)} stated, {len(enrichment.inferred_skills)} inferred skills; "
          f"unmapped {list(enrichment.unmapped) or 'none'}")

    print(f"\nTOP {len(results)} JOBS")
    for m in results:
        j = by_id[m.posting_id]
        print(f"\n#{m.rank:<2} {m.composite:.3f}  (rule {fmt(m.rule)}, semantic {fmt(m.semantic)})  {j.title}")
        print(f"    {j.location or 'location —'} · {fmt(j.budget, '.0f')} KES/day · {j.availability or 'availability —'}"
              f" · posting {m.posting_id}")
        if m.components:
            print("    rule: " + " · ".join(f"{c} {fmt(v, '.2f')}" for c, v in m.components.items()))
        if m.matched_skills:
            print("    matched: " + "; ".join(f"{s.skill_label} [{provenance(s, kg.label)}]" for s in m.matched_skills))

    print(f"\nTiming: startup {t_startup - t0:.2f} s (of which graph, data and job enrichment {t_build - t0:.2f} s); "
          f"query {1000 * (t_query - t_startup):.0f} ms")


if __name__ == "__main__":
    main()
