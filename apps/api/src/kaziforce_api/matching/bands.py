"""
Presentation bands for a composite score (docs/scoring-policy.md §6).

These affect **display only**. They never reorder results, never change a
score, and are not read by the evaluation, which computes P@K and MRR from the
full ranking (scripts/evaluate.py reads the frozen CSVs and never calls the
API). A result below DISPLAY_THRESHOLD is marked `below_threshold` so the
interface can hide it and show "No strong matches yet" when nothing remains.

The bounds were set from the development-split distribution of top-1 composite
scores, which separates cleanly: workers using a known term score 55-95, while
workers using a term withheld from the vocabulary score 35-59.
"""

from __future__ import annotations

DISPLAY_THRESHOLD = 55
STRONG, MODERATE, WEAK, BELOW = "strong", "moderate", "weak", "below_threshold"
BANDS = ((80, STRONG), (65, MODERATE), (DISPLAY_THRESHOLD, WEAK))


def match_score(composite: float) -> int:
    """The score a person sees: the composite as a whole number out of 100."""
    return round(composite * 100)


def band(composite: float) -> str:
    score = match_score(composite)
    for lower, name in BANDS:
        if score >= lower:
            return name
    return BELOW
