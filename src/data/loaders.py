"""
Data loading and preprocessing.

Loads worker/job data from the three-tier source strategy (see proposal
Section 3.2.1): Webmasters Kenya (primary) -> Jiji.co.ke (supplementary) ->
synthetic profiles grounded in KNBS/ESCO (fallback).
"""

import pandas as pd


def load_webmasters_data(path: str = "data/raw/webmasters/") -> pd.DataFrame:
    raise NotImplementedError


def load_jiji_data(path: str = "data/raw/jiji/") -> pd.DataFrame:
    raise NotImplementedError


def load_synthetic_data(path: str = "data/raw/synthetic/") -> pd.DataFrame:
    raise NotImplementedError


def clean_profile_text(df: pd.DataFrame) -> pd.DataFrame:
    """Remove formatting inconsistencies, handle missing values.

    TODO(Sprint 2): implement per proposal Section 3.2.2 (Data Processing)
    """
    raise NotImplementedError
