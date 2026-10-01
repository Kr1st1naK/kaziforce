"""
Kenya-specific informal trade vocabulary extension.

Validation pipeline (proposal Limitations section):
    1. LLM-assisted candidate generation for a given ESCO occupation/skill
    2. ESCO cross-reference (formal equivalent exists?)
    3. Manual review before the term is added to the graph.
"""


def generate_candidate_terms(esco_label: str) -> list[str]:
    """Prompt an LLM for candidate informal/vernacular terms for an ESCO label.

    TODO: implement LLM call, see LLM_API_KEY in .env
    """
    raise NotImplementedError


def validate_against_esco(term: str, formal_label: str) -> bool:
    """Cross-check whether the informal term plausibly maps to the formal ESCO label.

    TODO: implement using ESCO alternative labels (including Swahili where available).
    """
    raise NotImplementedError


def review_candidate(term: str, formal_label: str, sources: list[str]) -> dict:
    """Manually review a candidate term and return an approval record.

    Returns a dict with keys: informal_term, formal_term, approved, notes.
    """
    raise NotImplementedError