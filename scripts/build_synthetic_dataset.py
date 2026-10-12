"""
Builds the synthetic dataset (data/raw/synthetic/) from the frozen vocabulary.
See kaziforce_api.data.synthetic for the pipeline and data/raw/synthetic/README.md
for the files it writes.

Usage: python scripts/build_synthetic_dataset.py [--seed 42] [--workers-per-area 12]
           [--override 1=30 --override 11=30] [--jobs-per-area 8] [--distractors 200]
           [--rebuild-pools]
"""

from __future__ import annotations

import argparse
import json

from kaziforce_api.data.loaders import SYNTHETIC_DIR, build_synthetic_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers-per-area", type=int, default=12)
    parser.add_argument("--override", action="append", default=None, metavar="AREA_ID=N",
                        help="base workers for one area (default: 1=30 and 11=30)")
    parser.add_argument("--jobs-per-area", type=int, default=8)
    parser.add_argument("--distractors", type=int, default=200, help="Job Skill Set distractors (0 for none)")
    parser.add_argument("--rebuild-pools", action="store_true", help="rebuild skill pools from the ESCO subset")
    args = parser.parse_args()

    overrides = None if args.override is None else {int(k): int(v) for k, v in (o.split("=") for o in args.override)}
    manifest = build_synthetic_data(SYNTHETIC_DIR, rebuild_pools=args.rebuild_pools, n_distractors=args.distractors,
                                    seed=args.seed, workers_per_area=args.workers_per_area,
                                    area_overrides=overrides, jobs_per_area=args.jobs_per_area)
    print(json.dumps({k: manifest["counts"][k] for k in ("worker_rows", "jobs", "relevance_pairs")}))


if __name__ == "__main__":
    main()
