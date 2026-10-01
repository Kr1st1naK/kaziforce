"""
Knowledge graph construction.

Builds the domain-specific knowledge graph using NetworkX, combining:
  1. The ESCO taxonomy backbone (occupations, skills, hierarchical relations)
  2. The Kenya-specific informal trade vocabulary extension
  3. Worker and job profiles connected to their relevant skill/occupation nodes

See proposal Section 3.2.3 (Model Training) for the population sequence.
"""

import networkx as nx


def build_graph() -> nx.Graph:
    """Construct and return the enriched knowledge graph.

    TODO(Sprint 3):
        - Import ESCO backbone (occupations + skills, informal-relevant subset only)
        - Add Kenya vocabulary extension edges (informal term -> ESCO node)
        - Connect worker/job profile nodes to their skill/occupation nodes
    """
    graph = nx.Graph()
    return graph
