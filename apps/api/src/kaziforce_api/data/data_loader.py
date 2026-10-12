"""
DataLoader: read-only access to the frozen synthetic dataset as domain objects.

Profile methods (workers, jobs) return WorkerProfile / JobPosting only.
Evaluation methods (relevance, variants, split_of) expose ground truth and
bookkeeping, and must only be called from the evaluation side, never by a
scorer or enricher.

Unlike load_synthetic_data(), this class never regenerates the dataset: a
missing file raises FileNotFoundError (the dataset is frozen; see
data/raw/synthetic/README.md).
"""

from __future__ import annotations

import csv
import json
from functools import cached_property
from pathlib import Path

from kaziforce_api.data.loaders import SYNTHETIC_DIR
from kaziforce_api.data.models import JobPosting, WorkerProfile

SPLITS = ("development", "validation", "test")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; the synthetic dataset is committed, do not regenerate it")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _text(value: str) -> str | None:
    return value or None


def _number(value: str) -> float | None:
    return float(value) if value else None


class DataLoader:
    def __init__(self, path: Path = SYNTHETIC_DIR):
        self.path = Path(path)

    # Profiles (safe for scorers)

    def workers(self, split: str = "development") -> list[WorkerProfile]:
        if split not in SPLITS:
            raise ValueError(f"split must be one of {SPLITS}, not {split!r}")
        return [self._worker(r) for r in self._worker_rows if self._split_of_group[r["group_id"]] == split]

    def worker(self, worker_id: str, split: str = "development") -> WorkerProfile:
        for w in self.workers(split):
            if w.worker_id == worker_id:
                return w
        raise KeyError(f"worker {worker_id} is not in the {split} split")

    def jobs(self) -> list[JobPosting]:
        return [JobPosting(posting_id=r["posting_id"], title=r["title"], description=r["description"],
                           required_skills=tuple(json.loads(r["required_skills"])), location=_text(r["location"]),
                           availability=_text(r["availability"]), budget=_number(r["budget"]))
                for r in _read(self.path / "jobs.csv")]

    # Evaluation side only

    def relevance(self) -> set[tuple[str, str]]:
        return {(r["worker_id"], r["posting_id"]) for r in _read(self.path / "ground_truth" / "relevance.csv")}

    def variants(self) -> dict[str, str]:
        return {r["worker_id"]: r["variant"] for r in self._worker_rows}

    def split_of(self) -> dict[str, str]:
        return {r["worker_id"]: self._split_of_group[r["group_id"]] for r in self._worker_rows}

    def manifest(self) -> dict:
        return json.loads((self.path / "manifest.json").read_text(encoding="utf-8"))

    # Internals

    @cached_property
    def _worker_rows(self) -> list[dict]:
        return _read(self.path / "workers.csv")

    @cached_property
    def _split_of_group(self) -> dict[str, str]:
        return {r["group_id"]: r["split"] for r in _read(self.path / "splits.csv")}

    @staticmethod
    def _worker(r: dict) -> WorkerProfile:
        return WorkerProfile(worker_id=r["worker_id"], biography=r["biography"], skills=tuple(json.loads(r["skills"])),
                             location=_text(r["location"]), availability=_text(r["availability"]),
                             rate_expectation=_number(r["rate_expectation"]))
