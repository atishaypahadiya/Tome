# Tome

Codebase scanner and visualizer. Walk a directory, resolve imports, analyze git
history, and render the result as an interactive force-directed graph in your
browser — all from one command.

## Install

Requires Python 3.10+.

```bash
pip install -e .
```

## Usage

```bash
# Scan a codebase (writes ./tome-scan.json)
tome scan path/to/codebase

# Scan and immediately open the viewer
tome scan path/to/codebase --view

# View an existing scan
tome view tome-scan.json

# View the most recent scan in the current directory
tome view
```

### `tome scan` flags

| Flag | Description |
|---|---|
| `-o`, `--output PATH` | Output filename (default: `tome-scan.json`, auto-numbered) |
| `--no-git` | Skip git history analysis (faster) |
| `--diff PREV` | Diff against a previous scan JSON |
| `--summary` | Print a human-readable summary after scanning |
| `--json-compact` | Minified JSON output (default: pretty) |
| `-v`, `--verbose` | Print progress |
| `--view` | Serve and open the viewer immediately after scanning |

### `tome view` flags

| Flag | Description |
|---|---|
| `--port N` | Use a specific port (default: 7474, auto-increment if taken) |
| `--no-open` | Do not auto-open the browser |

## Development

The visualizer is a Vite/React app under `visualizer/`. To work on it:

```bash
cd visualizer
npm install
npm run dev
```

The dev server loads `sample-data.json` automatically when the API isn't reachable.

After making frontend changes, rebuild the bundle that ships with the Python package:

```bash
./scripts/bundle.sh
```

Commit both the source change and the updated `tome/_bundled/visualizer/`.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest -v
```
