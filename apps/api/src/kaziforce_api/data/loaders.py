"""
Data loading and preprocessing.

Three-tier source strategy (proposal Section 3.2.1):
    Webmasters Kenya (primary) -> Job Skill Set (supplementary) ->
    synthetic profiles (fallback).

Notebooks must call this module; they must not contain logic (see
notebooks/README.md).
"""

from __future__ import annotations

import ast
import json
import re
import unicodedata
import os
from pathlib import Path

import numpy as np
import pandas as pd


def _find_data_dir() -> Path:
    """Locate the repo-level data/ directory.

    Honours KAZIFORCE_DATA_DIR if set; otherwise walks up from this file
    (never from CWD) to the first ancestor containing data/README.md.
    """
    override = os.getenv("KAZIFORCE_DATA_DIR")
    if override:
        return Path(override).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "README.md").exists():
            return parent / "data"
    raise FileNotFoundError("data/ directory not found; set KAZIFORCE_DATA_DIR.")


DATA_DIR = _find_data_dir()
RAW_JOB_CSV = DATA_DIR / "raw/jobSkillData/all_job_post.csv"
ESCO_DIR = DATA_DIR / "raw/esco"
PROCESSED_DIR = DATA_DIR / "processed"
VOCABULARY_DIR = DATA_DIR / "vocabulary"

# Source loaders

def load_job_corpus(path: Path = RAW_JOB_CSV) -> pd.DataFrame:
    """Load the Job Skill Set (Mutlu, 2024) job-side corpus.

    Columns: job_id, category, job_title, job_description, job_skill_set.
    """
    if not path.exists():
        raise FileNotFoundError(f"Job corpus not found: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig")


def load_webmasters_data(path: Path = DATA_DIR / "raw/webmasters") -> pd.DataFrame:
    """Load Webmasters Kenya worker/job dataset (primary source).

    TODO: implement once industry partner data is provided.
    """
    raise NotImplementedError


def load_esco_data(path: Path = ESCO_DIR) -> dict[str, pd.DataFrame]:
    """Load ESCO taxonomy backbone (occupations, skills, hierarchies, labels).

    Expected files in `path`:
        occupations_en.csv
        skills_en.csv
        occupationSkillRelations_en.csv
        skillHierarchy_en.csv

    TODO: implement after ESCO download.
    """
    raise NotImplementedError


def load_synthetic_data(path: Path = DATA_DIR / "raw/synthetic") -> pd.DataFrame:
    """Load generated synthetic worker profiles (fallback source).

    TODO: implement once kaziforce_api/data/synthetic.py is written.
    """
    raise NotImplementedError


# Text cleaning primitives
_BULLET_RE = re.compile(r"[\u2022\u2023\u25E6\u2043\u2219\uf0b7]")
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_MULTINL_RE = re.compile(r"\n\s*\n+")
_PUNCT_SPACE_RE = re.compile(r"\s+([.,;:!?])")
_SKILL_STRIP_RE = re.compile(r"[^\w\s\-\+/#\.]")


def clean_text(x) -> str:
    if pd.isna(x):
        return np.nan
    x = unicodedata.normalize("NFKC", str(x))
    x = x.replace("\r\n", "\n").replace("\r", "\n")
    x = _BULLET_RE.sub(" ", x)
    x = _HTML_RE.sub(" ", x)
    x = _WS_RE.sub(" ", x)
    x = _MULTINL_RE.sub("\n", x)
    x = _PUNCT_SPACE_RE.sub(r"\1", x)
    return x.strip()


def parse_skill_set(s) -> list[str]:
    if pd.isna(s):
        return []
    s = str(s).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [
                str(i).strip() for i in parsed
                if i is not None and str(i).strip()
                and str(i).lower() not in {"nan", "none", "null"}
            ]
        if isinstance(parsed, str):
            return [parsed.strip()] if parsed.strip() else []
    except (ValueError, SyntaxError):
        pass
    parts = re.split(r",\s*", s.strip("[]"))
    return [
        p.strip().strip("'\"") for p in parts
        if p.strip().strip("'\"") and p.strip().strip("'\"").lower() not in {"nan", "none", "null"}
    ]


def normalize_skill(s) -> str:
    if pd.isna(s):
        return np.nan
    s = clean_text(s)
    if not s:
        return np.nan
    s = s.lower().replace("&", " and ")
    s = _SKILL_STRIP_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else np.nan

# Orchestration
def preprocess_jobs(df: pd.DataFrame, out_dir: Path = PROCESSED_DIR) -> dict:
    """Clean, dedupe, parse, and export the job-side corpus."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {"original_rows": int(len(df))}
    df = df.copy()

    # --- Text cleaning ---
    df["job_title_clean"] = df["job_title"].apply(clean_text)
    df["job_description_clean"] = df["job_description"].apply(clean_text)
    df["category_clean"] = df["category"].apply(
        lambda x: clean_text(x).lower() if pd.notna(x) else np.nan
    )
    df["job_title_norm"] = df["job_title_clean"].str.lower()
    df["job_description_norm"] = df["job_description_clean"].str.lower()

    # --- Skills parse + normalise ---
    df["job_skill_list"] = df["job_skill_set"].apply(parse_skill_set)
    df["job_skill_list"] = df["job_skill_list"].apply(
        lambda xs: sorted(set(xs), key=lambda s: s.lower())
    )
    df["job_skill_normalized_list"] = df["job_skill_list"].apply(
        lambda xs: sorted(set(
            normalize_skill(x) for x in xs if pd.notna(normalize_skill(x))
        ))
    )
    df["job_skill_count"] = df["job_skill_list"].apply(len)

    # --- Deduplicate ---
    before = len(df); df = df.drop_duplicates(keep="first").copy()
    report["dropped_exact_duplicates"] = before - len(df)

    dups = df[df.duplicated(subset=["job_id"], keep=False)].copy()
    if len(dups):
        dups.to_csv(out_dir / "duplicate_job_ids.csv", index=False)

    before = len(df); df = df.drop_duplicates(subset=["job_id"], keep="first").copy()
    report["dropped_duplicate_job_id"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates(
        subset=["job_title_clean", "job_description_clean", "category_clean"],
        keep="first",
    ).copy()
    report["dropped_near_duplicates"] = before - len(df)

    # --- Usability flags ---
    df["has_title"] = df["job_title_clean"].fillna("").str.len() > 0
    df["has_description"] = df["job_description_clean"].fillna("").str.len() > 0
    df["has_skills"] = df["job_skill_list"].apply(len) > 0
    df["usable_for_semantic"] = df["has_description"]
    df["usable_for_rule"] = df["has_skills"]
    df["usable_for_kg"] = df["has_title"] & df["has_skills"]

    report["usable_for_semantic"] = int(df["usable_for_semantic"].sum())
    report["usable_for_rule"] = int(df["usable_for_rule"].sum())
    report["usable_for_kg"] = int(df["usable_for_kg"].sum())
    report["final_rows"] = int(len(df))

    df[~df["has_title"] & ~df["has_description"] & ~df["has_skills"]].to_csv(
        out_dir / "unusable_jobs.csv", index=False
    )

    # --- Long job-skill table ---
    skills_long = df.explode("job_skill_list").dropna(subset=["job_skill_list"]).copy()
    skills_long["skill_original"] = skills_long["job_skill_list"].astype(str).str.strip()
    skills_long["skill_normalized"] = skills_long["skill_original"].apply(normalize_skill)
    skills_long = skills_long[skills_long["skill_normalized"].notna()].copy()
    skills_long = skills_long[
        ["job_id", "category_clean", "job_title_clean",
         "skill_original", "skill_normalized"]
    ].drop_duplicates(subset=["job_id", "skill_normalized"])
    report["long_skill_rows"] = int(len(skills_long))

    # --- Skill vocabulary ---
    skill_vocab = (
        skills_long.groupby("skill_normalized")
        .agg(frequency=("job_id", "nunique"), example_original=("skill_original", "first"))
        .reset_index()
        .sort_values(["frequency", "skill_normalized"], ascending=[False, True])
    )
    skill_vocab["esco_skill_id"] = None
    skill_vocab["mapping_status"] = "unmapped"
    skill_vocab["mapping_notes"] = None
    report["unique_normalized_skills"] = int(len(skill_vocab))

    # --- Templates ---
    pd.DataFrame(columns=[
        "skill_normalized", "esco_skill_id", "esco_preferred_label",
        "mapping_status", "source", "notes",
    ]).to_csv(out_dir / "esco_skill_mapping_template.csv", index=False)

    VOCABULARY_DIR.mkdir(parents=True, exist_ok=True)
    kenya_path = VOCABULARY_DIR / "kenya_informal_vocab_template.csv"
    if not kenya_path.exists():
        pd.DataFrame(columns=[
            "informal_term", "formal_term", "esco_occupation_uri",
            "esco_skill_uri", "source", "validated",
        ]).to_csv(kenya_path, index=False)

    # --- Save outputs ---
    jobs_clean = df.copy()
    jobs_clean["job_skill_list_json"] = jobs_clean["job_skill_list"].apply(json.dumps)
    jobs_clean["job_skill_normalized_list_json"] = (
        jobs_clean["job_skill_normalized_list"].apply(json.dumps)
    )
    jobs_clean.drop(
        columns=["job_skill_list", "job_skill_normalized_list"], errors="ignore"
    ).to_csv(out_dir / "jobs_clean.csv", index=False)
    skills_long.to_csv(out_dir / "job_skills_long.csv", index=False)
    skill_vocab.to_csv(out_dir / "skill_vocab.csv", index=False)

    # --- Report ---
    with open(out_dir / "preprocessing_report.txt", "w", encoding="utf-8") as f:
        f.write("JOB CORPUS PREPROCESSING REPORT\n" + "=" * 40 + "\n")
        for k, v in report.items():
            f.write(f"{k}: {v}\n")

    return report