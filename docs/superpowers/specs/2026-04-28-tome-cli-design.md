# Tome CLI — Design Spec

**Date:** 2026-04-28
**Status:** Approved (pending implementation plan)

## Problem

Tome currently ships as two disconnected pieces: a Python scanner (`scan.py` + `scanner/`) that emits JSON, and a Vite/React visualizer (`visualizer/`) that consumes it. To go from "scan a codebase" to "see the graph" today, you run a Python script, find the JSON it wrote, then start a separate dev server and load the file by hand. There is no single command, no installable entry point, and no obvious way to share the tool with someone else.

This spec defines a unified `tome` CLI with three subcommands — `scan`, `view`, and `scan --view` — and the packaging needed to install it as one tool.

## Goals

- One command (`tome`) covers the full workflow: scan → serve → render.
- `pip install -e .` is the only setup step. No Node required to run the tool.
- The existing scanner behavior and JSON output format are preserved exactly. All current `scan.py` flags carry over.
- Frontend developers can still run `npm run dev` against sample data without the Python server.

## Non-Goals

- PyPI publishing, Homebrew formula, or standalone binary distribution.
- Live reload, WebSocket, or push-based updates from scanner to viewer.
- Multi-user / hosted deployment. The viewer is a localhost-only dev tool.
- Authentication, HTTPS, remote scanning.

## CLI Interface

Single binary `tome` with three subcommands.

```
tome scan <path>                    # scan, write ./tome-scan.json (auto-numbered: tome-scan 2.json, tome-scan 3.json, ... if names already exist)
tome scan <path> -o results.json    # custom output path
tome scan <path> --no-git           # skip git history analysis
tome scan <path> -v                 # verbose
tome scan <path> --view             # scan, then immediately serve and open browser

tome view                           # serve most recent *.json scan in cwd
tome view results.json              # serve a specific file

tome --help / tome <subcmd> --help  # standard argparse help
```

Existing `scan.py` flags carry over unchanged: `--diff <file>`, `--summary`, `--json-compact`, `-o`, `-v`, `--no-git`.

New flags on `view`:

- `--port N` — pin a specific port (errors if taken)
- `--no-open` — don't auto-open the browser (useful for SSH / headless)

## Packaging & Distribution

### Repository layout

```
tome/
├── pyproject.toml          # entry point: tome = "tome.cli:main"
├── tome/
│   ├── __init__.py
│   ├── cli.py              # argparse, subcommand dispatch (replaces scan.py)
│   ├── server.py           # http.server-based static + JSON injection
│   ├── scanner/            # moved from top-level scanner/
│   │   ├── walker.py
│   │   ├── analyzer.py
│   │   ├── differ.py
│   │   ├── git_analyzer.py
│   │   ├── output.py
│   │   └── parsers/
│   └── _bundled/
│       └── visualizer/     # built dist/, shipped with the package, committed to git
├── visualizer/             # Vite source — NOT shipped in the wheel
├── docs/
└── scripts/
    └── bundle.sh           # builds visualizer and copies dist/ → tome/_bundled/visualizer/
```

### Packaging decisions

- **Bundled visualizer is committed to git.** Rationale: this is a dev tool, not a published library. One-step install (`pip install -e .` with no Node prerequisite) matters more than diff cleanliness. Mark the bundle directory as `linguist-generated` in `.gitattributes` so PRs don't show its diffs.
- **Scanner moves under `tome/`.** Standard Python package layout. Imports become `from tome.scanner import ...`. One-time refactor.
- **Resource resolution via `importlib.resources`.** Lets the bundle path resolve correctly from both source checkouts and installed wheels.
- **Python ≥ 3.10** for modern `importlib.resources` ergonomics.
- **Distribution scope (v1):** local `pip install -e .` only. No PyPI, no Homebrew, no PyInstaller binary.

### Bundle workflow

1. Frontend dev edits `visualizer/src/...`
2. `npm run build` from `visualizer/` produces `visualizer/dist/`
3. `scripts/bundle.sh` copies `visualizer/dist/*` → `tome/_bundled/visualizer/`
4. Commit both the source change and the bundle update in the same commit

`pyproject.toml` declares `tome/_bundled/**` as package data so the bundle ships with `pip install`.

## Server & Data Loading

### Server (`tome/server.py`)

- Built on `http.server.ThreadingHTTPServer` — no Flask, FastAPI, or other web-framework dependency
- Serves static files from `tome/_bundled/visualizer/`
- Special-cases one route: `GET /api/scan-data.json` → returns the scan JSON loaded into memory at startup
- All other routes: static file lookup, with SPA fallback to `index.html` for unknown paths
- Default port `7474`. If taken, auto-increment up to 10 attempts (`7475`, `7476`, ...) then error out
- `--port N` pins the port explicitly and errors immediately if it's taken (no auto-increment when the user is explicit)
- `webbrowser.open(...)` after the server is listening, unless `--no-open`
- Ctrl+C → clean exit, no traceback (handle `KeyboardInterrupt` at the top level)

### Visualizer data loading

The visualizer currently fetches `sample-data.json` (hardcoded). Change this to:

1. Try `GET /api/scan-data.json` first
2. On 404 (or any non-200), fall back to `GET /sample-data.json`

This means:

- `tome view <file>` → API returns 200, real scan data loads
- `npm run dev` standalone → API doesn't exist, sample data loads

The fallback is two lines of fetch logic and lets frontend devs work the UI with no Python running.

## Migration

This is a one-shot migration, not a phased rollout. Nothing depends on the current layout externally.

| Current                            | After                              |
| ---------------------------------- | ---------------------------------- |
| `scan.py`                          | `tome/cli.py` (with `scan` subcmd) |
| `scanner/*.py`                     | `tome/scanner/*.py`                |
| `visualizer/dist/`                 | also copied to `tome/_bundled/visualizer/` |
| (none)                             | `tome/server.py` (new)             |
| (none)                             | `pyproject.toml` (new)             |
| (none)                             | `scripts/bundle.sh` (new)          |

Visualizer source (`visualizer/src/`, `package.json`, `vite.config.js`, etc.) stays in place. Only the build output gets duplicated into the bundle.

The two existing `conscious-2.0 scan*.json` files at the repo root are scan artifacts from prior runs — leave them. They are not source.

## Testing

Scope to "verify the migration didn't break anything" — not exhaustive coverage.

- **Scanner regression:** scan a known fixture (the tome repo itself), assert the output JSON has `files`, `edges`, `metadata`, and `runtime_edges` keys. One smoke test, not full coverage.
- **CLI dispatch:** subprocess tests for `tome --help`, `tome scan --help`, `tome view --help` — assert exit 0 and that expected subcommand names appear in output.
- **Server:** start on an ephemeral port (`port=0`), then:
  - `GET /api/scan-data.json` → 200 with the loaded JSON
  - `GET /` → 200 with HTML
  - `GET /nonexistent` → 200 with index.html (SPA fallback)
- **Visualizer:** no automated tests. The fetch fallback is two lines. Manual verification:
  - `cd visualizer && npm run dev` → loads `sample-data.json`
  - `tome view <scan>` → loads scan via API

## Definition of Done

- `pip install -e .` succeeds on a clean clone with no Node prerequisite
- `tome scan .` produces JSON byte-equivalent to today's `python scan.py .` (modulo timestamps)
- `tome view <file>` opens the browser and the graph renders
- `tome scan . --view` works end-to-end in a single command
- All listed tests pass
- README updated with the new install + usage instructions

## Open Questions

None. All design decisions are settled.
