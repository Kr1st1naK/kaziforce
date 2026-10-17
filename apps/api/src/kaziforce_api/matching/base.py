"""The interface every scorer realises, so a configuration is just an (enricher, scorer) pair."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, MatchScore


class Scorer(ABC):
    @abstractmethod
    def score_all(self, worker: EnrichedWorker, jobs: Sequence[EnrichedJob]) -> list[MatchScore]:
        """One unranked MatchScore per job, in job order; `composite` is the score used for ranking."""
