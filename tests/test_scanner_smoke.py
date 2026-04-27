"""Smoke test: scanning a small fixture produces JSON with expected top-level keys.

This test exists to guard the scanner refactor (top-level scanner/ -> tome/scanner/).
It does NOT validate scanner correctness in detail - just that the public output
shape is preserved.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_TOP_KEYS = {"files", "edges", "metadata", "runtime_edges", "env_vars", "entry_points"}


def test_scan_repo_produces_expected_keys(tmp_path):
    """Scanning the tome repo itself should produce JSON with all expected keys."""
    out = tmp_path / "scan.json"
    # We invoke via subprocess to exercise the real entry point.
    # Switch this command in Task 6 once `tome` is installed.
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scan.py"), str(REPO_ROOT), "-o", str(out), "--no-git"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"scan failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    assert out.exists(), "scan did not produce output file"

    data = json.loads(out.read_text())
    missing = EXPECTED_TOP_KEYS - set(data.keys())
    assert not missing, f"missing top-level keys: {missing}"
    assert isinstance(data["files"], list) and len(data["files"]) > 0
    assert isinstance(data["edges"], list)
    assert isinstance(data["metadata"], dict)
    assert "total_files" in data["metadata"]
