"""Git integration for the Tome scanner.

Provides change frequency, contributor, and hotspot analysis by
querying the local git history via subprocess.  Uses only the
Python standard library (subprocess) and targets Python 3.8+.
"""

import subprocess
from typing import Dict, List, Optional


def _normalize_path(path: str) -> str:
    """Strip leading './' and normalize to forward slashes."""
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def _run_git(args: List[str]) -> Optional[subprocess.CompletedProcess]:
    """Run a git command and return the CompletedProcess, or None on failure."""
    try:
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def is_git_repo(path: str) -> bool:
    """Return True if *path* is inside a git work tree."""
    result = _run_git(["-C", path, "rev-parse", "--is-inside-work-tree"])
    return result is not None and result.returncode == 0


def get_change_frequency(repo_path: str, months: int = 6) -> Dict[str, int]:
    """Return a dict mapping relative file path -> number of commits in the period.

    Uses a single bulk ``git log`` call to collect all changed file names.
    """
    result = _run_git([
        "-C", repo_path,
        "log",
        "--pretty=format:",
        "--name-only",
        "--since={} months ago".format(months),
    ])
    if result is None or result.returncode != 0:
        return {}

    counts: Dict[str, int] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        normalized = _normalize_path(line)
        counts[normalized] = counts.get(normalized, 0) + 1
    return counts


def get_file_git_info(
    repo_path: str, file_path: str, months: int = 6
) -> Dict:
    """Return git metadata for a single file.

    Returns::

        {"change_count": int, "last_modified": str | None, "contributors": int}
    """
    rel = _normalize_path(file_path)

    # --- change count ---
    result = _run_git([
        "-C", repo_path,
        "log", "--oneline",
        "--since={} months ago".format(months),
        "--", rel,
    ])
    if result is not None and result.returncode == 0:
        change_count = len([l for l in result.stdout.splitlines() if l.strip()])
    else:
        change_count = 0

    # --- last modified ---
    last_modified: Optional[str] = None
    result = _run_git([
        "-C", repo_path,
        "log", "-1",
        "--format=%aI",
        "--", rel,
    ])
    if result is not None and result.returncode == 0:
        date_line = result.stdout.strip()
        if date_line:
            # %aI gives ISO-8601 e.g. 2026-02-22T14:30:00+05:30 — keep date part
            last_modified = date_line[:10]

    # --- contributors ---
    result = _run_git([
        "-C", repo_path,
        "log",
        "--format=%aN",
        "--since={} months ago".format(months),
        "--", rel,
    ])
    if result is not None and result.returncode == 0:
        names = {n.strip() for n in result.stdout.splitlines() if n.strip()}
        contributors = len(names)
    else:
        contributors = 0

    return {
        "change_count": change_count,
        "last_modified": last_modified,
        "contributors": contributors,
    }


def _parse_bulk_log(output: str):
    """Parse the output of ``git log --format="%aI %aN" --name-only``.

    Each commit block looks like::

        2026-02-22T14:30:00+05:30 Alice
        src/foo.py
        src/bar.py

        2026-02-21T10:00:00+05:30 Bob
        src/baz.py

    Returns two dicts:
        authors  — {normalized_path: set of author names}
        dates    — {normalized_path: latest ISO date string (YYYY-MM-DD)}
    """
    authors: Dict[str, set] = {}
    dates: Dict[str, str] = {}

    lines = output.splitlines()
    i = 0
    while i < len(lines):
        # Skip blank lines between commit blocks
        if not lines[i].strip():
            i += 1
            continue

        # The format line: "<ISO-datetime> <author-name>"
        format_line = lines[i].strip()
        i += 1

        # Split on first space to get the datetime token; the rest is author
        parts = format_line.split(" ", 1)
        if len(parts) < 2:
            # Malformed line — skip
            continue

        date_token = parts[0]  # e.g. 2026-02-22T14:30:00+05:30
        author = parts[1].strip()

        # Extract YYYY-MM-DD from the ISO datetime
        commit_date = date_token[:10] if len(date_token) >= 10 else None

        # Collect file names until blank line or end of output
        while i < len(lines) and lines[i].strip():
            fpath = _normalize_path(lines[i].strip())
            i += 1

            # authors
            if fpath not in authors:
                authors[fpath] = set()
            authors[fpath].add(author)

            # dates — keep the most recent (first encountered because git log
            # is reverse-chronological by default)
            if commit_date and fpath not in dates:
                dates[fpath] = commit_date

    return authors, dates


def analyze_git(
    repo_path: str,
    files: List[Dict],
    months: int = 6,
    verbose: bool = False,
) -> None:
    """Enrich each file dict with git metadata.

    Sets ``file['git']`` to a dict with keys ``change_count``,
    ``last_modified``, ``contributors``, and ``hotspot_score``, or
    ``None`` when the path is not a git repository.

    This function mutates *files* in place and returns nothing.
    """
    # 1. Check if we are in a git repo
    if not is_git_repo(repo_path):
        for f in files:
            f["git"] = None
        return

    # 2. Bulk change frequency
    change_freq = get_change_frequency(repo_path, months)

    # 3. Bulk last_modified + contributors via a single git log call
    result = _run_git([
        "-C", repo_path,
        "log",
        "--format=%aI %aN",
        "--name-only",
        "--since={} months ago".format(months),
    ])

    if result is not None and result.returncode == 0:
        bulk_authors, bulk_dates = _parse_bulk_log(result.stdout)
    else:
        bulk_authors, bulk_dates = {}, {}

    # 4. Populate each file
    total_hotspot = 0
    files_with_git = 0

    for f in files:
        rel = _normalize_path(f["path"])

        change_count = change_freq.get(rel, 0)
        last_modified = bulk_dates.get(rel)
        contributors = len(bulk_authors.get(rel, set()))
        imported_by = f.get("imported_by", [])
        hotspot_score = change_count * len(imported_by)

        f["git"] = {
            "change_count": change_count,
            "last_modified": last_modified,
            "contributors": contributors,
            "hotspot_score": hotspot_score,
        }

        if change_count > 0:
            files_with_git += 1
        total_hotspot += hotspot_score

    # 5. Optional verbose summary
    if verbose:
        print("\n  Git analysis complete:")
        print("    Files with recent changes: {}".format(files_with_git))
        print("    Total files analyzed: {}".format(len(files)))
        print("    Total hotspot score: {}".format(total_hotspot))
        if change_freq:
            top = sorted(change_freq.items(), key=lambda kv: kv[1], reverse=True)[:5]
            print("    Most changed files:")
            for path, count in top:
                print("      {} ({} commits)".format(path, count))
