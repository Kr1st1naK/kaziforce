"""Code and data provenance recorded with every generated result (git commit, uncommitted changes)."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def git_commit() -> str:
    return _git("rev-parse", "HEAD")


def has_uncommitted_changes() -> bool:
    """True if tracked files differ from HEAD (untracked files are ignored)."""
    return bool(_git("status", "--porcelain", "--untracked-files=no"))
