"""
Kenya-specific informal trade vocabulary extension.

Three-layer validation pipeline (see proposal Section 1.2.1 / Limitations):
  1. LLM-assisted candidate term generation for a given ESCO occupation/skill
  2. Cross-check against real worker-listed language (Jiji.co.ke)
  3. Cross-check against Mandla (crowd-sourced Kenyan-language dictionary)
  Only terms corroborated by at least one independent source proceed to
  manual review before being added to the graph.
"""


def generate_candidate_terms(esco_label: str) -> list[str]:
    """Prompt an LLM for candidate informal/vernacular terms for an ESCO label.

    TODO(Sprint 2): implement LLM call, see LLM_API_KEY in .env
    """
    raise NotImplementedError


def validate_against_jiji(term: str) -> bool:
    """Check whether a candidate term appears in real Jiji.co.ke listings.

    TODO(Sprint 2): implement once Jiji data is collected (data/raw/jiji/)
    """
    raise NotImplementedError


def validate_against_mandla(term: str) -> bool:
    """Cross-check a candidate term's meaning against the Mandla dictionary.

    TODO(Sprint 2): implement Mandla lookup
    """
    raise NotImplementedError
