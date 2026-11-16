"""The interface every explainer realises, so explanation generation is a component in
its own right rather than logic scattered through the API and the interface (NFR-03)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile

from kaziforce_api.explainability.models import Explanation


class Explainer(ABC):
    @abstractmethod
    def explain(self, worker: WorkerProfile, job: JobPosting, match: MatchScore) -> Explanation:
        """One Explanation for a completed match.

        Reads a finished MatchScore and never feeds back into scoring or ranking, so
        generating an explanation cannot change any other metric.
        """
