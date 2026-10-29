"""
Evaluates the recommendation configurations on the development split.

Each development worker ranks all 280 postings under each configuration; P@3,
P@5, P@10 and MRR are reported overall and per variant, with the
knowledge-graph ablation pairs and per-query response times. Every result is
written to a run folder with the code and data versions it came from:

    results/dev/<YYYYMMDD-HHMMSS>_<commit>/   metrics.md, metrics.csv, per_query.csv, run.json

Refuses to run on a working tree with uncommitted changes (so the recorded
commit is the code that ran) unless --allow-dirty is given, which run.json
records. Partial runs (--max-queries) go to results/scratch/, which is not
committed.

Usage: python scripts/evaluate.py [--configs full keyword ...] [--max-queries N] [--allow-dirty]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.evaluation.evaluator import Evaluator
from kaziforce_api.evaluation.report import write_run
from kaziforce_api.explainability.explain import ExplanationGenerator
from kaziforce_api.matching.hybrid import HybridWeights
from kaziforce_api.matching.rule_based import RuleBasedWeights
from kaziforce_api.matching.semantic import MODEL_NAME, MODEL_REVISION, SemanticScorer, job_text
from kaziforce_api.pipeline import CONFIGURATIONS, KG_ABLATION_PAIRS, TIE_BREAK_SEED, build_recommender
from kaziforce_api.provenance import git_commit, has_uncommitted_changes
from kaziforce_kg.builder import KnowledgeGraphBuilder

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"
PACKAGES = ("numpy", "pandas", "networkx", "torch", "sentence-transformers", "transformers")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def processor() -> str:
    if sys.platform == "darwin":
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    return platform.processor() or platform.machine()


def metadata(args, recommenders, startup: float, n_queries: int) -> dict:
    synthetic = DATA / "raw/synthetic"
    manifest = json.loads((synthetic / "manifest.json").read_text())
    return {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "split": "development", "queries": n_queries, "ks": [3, 5, 10], "seed": TIE_BREAK_SEED,
        "partial": args.max_queries is not None,
        "configurations": {n: {"enricher": type(r.enricher).__name__, "scorer": type(r.scorer).__name__}
                           for n, r in recommenders.items()},
        "weights": {"rule_based": asdict(RuleBasedWeights()), "hybrid": asdict(HybridWeights()),
                    "bm25": {"k1": 1.2, "b": 0.75}},
        "semantic_model": {"name": MODEL_NAME, "revision": MODEL_REVISION},
        "git": {"commit": git_commit(), "uncommitted_changes": has_uncommitted_changes(),
                "allow_dirty": args.allow_dirty},
        "data": {"synthetic_generator": manifest["generator"], "synthetic_seed": manifest["seed"],
                 "synthetic_inputs_sha256": manifest["inputs_sha256"],
                 "files_sha256": {str(p.relative_to(DATA)): sha256(p) for p in (
                     synthetic / "workers.csv", synthetic / "jobs.csv", synthetic / "splits.csv",
                     synthetic / "ground_truth/relevance.csv", DATA / "vocabulary/aliases.csv")},
                 "kg_outputs_sha256": json.loads((DATA / "kg/manifest.json").read_text())["outputs_sha256"]},
        "scoring_policy_sha256": sha256(REPO_ROOT / "docs/scoring-policy.md"),
        "startup_seconds": round(startup, 2),
        "packages": {p: importlib.metadata.version(p) for p in PACKAGES},
        "machine": {"platform": platform.platform(), "processor": processor(), "python": platform.python_version()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--configs", nargs="+", default=list(CONFIGURATIONS), choices=list(CONFIGURATIONS))
    parser.add_argument("--max-queries", type=int, help="evaluate only the first N workers (written to results/scratch/)")
    parser.add_argument("--allow-dirty", action="store_true", help="run despite uncommitted changes (recorded)")
    args = parser.parse_args()
    if has_uncommitted_changes() and not args.allow_dirty:
        parser.error("uncommitted changes: commit first so the run maps to a commit, or pass --allow-dirty")

    start = time.perf_counter()
    loader = DataLoader()
    jobs, kg, semantic = loader.jobs(), KnowledgeGraphBuilder().build(), SemanticScorer()
    recommenders = {n: build_recommender(n, jobs, kg=kg, semantic=semantic) for n in args.configs}
    if any(type(r.scorer).__name__ in ("SemanticScorer", "HybridScorer") for r in recommenders.values()):
        semantic.embed([job_text(j) for j in next(iter(recommenders.values())).jobs])
    startup = time.perf_counter() - start

    evaluator = Evaluator(loader, recommenders, max_queries=args.max_queries,
                          explainer=ExplanationGenerator(kg))
    print(f"Evaluating {len(recommenders)} configurations on the development split (startup {startup:.1f} s)")
    result = evaluator.run()
    n_queries = len({q.worker_id for q in result.queries})
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = REPO_ROOT / "results" / ("scratch" if args.max_queries else "dev")
    out = write_run(result, metadata(args, recommenders, startup, n_queries), base / f"{stamp}_{git_commit()[:7]}",
                    ablation_pairs=[p for p in KG_ABLATION_PAIRS if set(p) <= set(args.configs)])
    print((out / "metrics.md").read_text())
    print(f"Written to {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
