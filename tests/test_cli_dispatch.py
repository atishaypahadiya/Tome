"""CLI dispatch smoke tests via subprocess."""

import subprocess


def _run(*args):
    return subprocess.run(["tome", *args], capture_output=True, text=True)


def test_top_level_help_lists_subcommands():
    r = _run("--help")
    assert r.returncode == 0
    assert "scan" in r.stdout
    assert "view" in r.stdout


def test_scan_help():
    r = _run("scan", "--help")
    assert r.returncode == 0
    for flag in ("--output", "--no-git", "--diff", "--summary", "--view"):
        assert flag in r.stdout, f"missing flag in scan --help: {flag}"


def test_view_help():
    r = _run("view", "--help")
    assert r.returncode == 0
    for flag in ("--port", "--no-open"):
        assert flag in r.stdout, f"missing flag in view --help: {flag}"
