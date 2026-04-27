#!/usr/bin/env python3
"""Tome -- codebase scanner and visualization data generator.

Usage:
    python scan.py /path/to/codebase
    python scan.py /path/to/codebase -o custom.json
    python scan.py /path/to/codebase --verbose --summary
    python scan.py /path/to/codebase --diff previous-scan.json
    python scan.py /path/to/codebase --no-git
"""

import argparse
import glob as _glob
import os
import re
import sys
import time

from tome.scanner.walker import walk_directory
from tome.scanner.parsers import resolve_all_imports
from tome.scanner.analyzer import analyze
from tome.scanner.output import format_output, write_output
from tome.scanner.git_analyzer import analyze_git
from tome.scanner.differ import diff_scans


def _auto_output_name(codebase_path):
    base = os.path.basename(os.path.abspath(codebase_path))
    prefix = f"{base} scan"
    existing = _glob.glob(f"{prefix}*.json")
    if not existing:
        return f"{prefix}.json"
    highest = 1
    pat = re.compile(re.escape(prefix) + r'(?:\s+(\d+))?\.json$')
    for name in existing:
        m = pat.match(name)
        if m:
            num = int(m.group(1)) if m.group(1) else 1
            highest = max(highest, num)
    return f"{prefix} {highest + 1}.json"


def _print_summary(data):
    files = data.get('files', [])
    edges = data.get('edges', [])
    issues = data.get('issues', {})
    runtime = data.get('runtime_edges', [])
    env_vars = data.get('env_vars', [])
    entry_pts = data.get('entry_points', [])
    meta = data.get('metadata', {})

    # File breakdown by status
    status_counts = {}
    code_exts = {'.py', '.js', '.jsx', '.ts', '.tsx'}
    for f in files:
        st = f.get('status', 'active')
        status_counts[st] = status_counts.get(st, 0) + 1
    code = sum(1 for f in files if f.get('extension') in code_exts)
    data_n = status_counts.get('data', 0) + status_counts.get('config', 0)
    docs = status_counts.get('documentation', 0)
    build = status_counts.get('build', 0) + status_counts.get('namespace', 0)
    other = len(files) - code - data_n - docs - build
    if other < 0:
        other = 0

    # Edge breakdown
    edge_types = {}
    for e in edges:
        t = e.get('type', 'strong')
        edge_types[t] = edge_types.get(t, 0) + 1

    # Runtime edge breakdown
    rt_types = {}
    for e in runtime:
        t = e.get('type', 'http')
        rt_types[t] = rt_types.get(t, 0) + 1

    # Circular breakdown
    circ = issues.get('circular', [])
    runtime_circ = sum(1 for c in circ if c.get('severity') == 'runtime')
    struct_circ = len(circ) - runtime_circ

    # Hotspots
    hotspots = sum(1 for f in files if (f.get('git') or {}).get('hotspot_score', 0) > 50)

    total_loc = meta.get('total_loc', 0)

    print()
    print("  Tome Scan Complete")
    print("  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    print(f"  Path: {meta.get('scanned_path', '?')}")
    print(f"  Files: {len(files)} ({code} code, {data_n} data/config, {docs} docs, {build} build, {other} other)")
    print(f"  LOC: {total_loc:,}")
    print(f"  Modules: {meta.get('total_modules', 0)}")

    edge_parts = []
    for t in ('strong', 'lazy', 'conditional', 'type_only'):
        c = edge_types.get(t, 0)
        if c:
            edge_parts.append(f"{c} {t}")
    print(f"  Edges: {len(edges)} ({', '.join(edge_parts) if edge_parts else 'none'})")

    if runtime:
        rt_parts = [f"{c} {t}" for t, c in sorted(rt_types.items()) if c]
        print(f"  Runtime edges: {len(runtime)} ({', '.join(rt_parts)})")

    print()
    print("  Issues:")
    print(f"    Code orphans: {len(issues.get('orphans', []))}")
    print(f"    Dead imports: {len(issues.get('dead_imports', []))}")
    print(f"    Circular deps: {len(circ)} ({runtime_circ} runtime, {struct_circ} structural)")
    if hotspots:
        print(f"    Hotspots: {hotspots} files with score > 50")
    if env_vars:
        print(f"    Env vars: {len(env_vars)} tracked")

    if entry_pts:
        print()
        names = [os.path.basename(p) if '/' in p else p for p in entry_pts[:8]]
        print(f"  Entry points: {', '.join(names)}")
    print()


def main():
    ap = argparse.ArgumentParser(description='Tome: scan a codebase and output structured JSON.')
    ap.add_argument('path', help='Path to the codebase directory')
    ap.add_argument('-o', '--output', default=None, help='Output file name (default: auto)')
    ap.add_argument('--verbose', '-v', action='store_true', help='Print progress')
    ap.add_argument('--no-git', action='store_true', help='Skip git analysis')
    ap.add_argument('--diff', metavar='PREV', default=None, help='Diff against a previous scan JSON')
    ap.add_argument('--json-pretty', action='store_true', help='Pretty-print JSON (default: pretty)')
    ap.add_argument('--json-compact', action='store_true', help='Minified JSON output')
    ap.add_argument('--summary', action='store_true', help='Print human-readable summary')
    args = ap.parse_args()

    root = args.path
    if not os.path.isdir(root):
        print(f"Error: '{root}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)
    root = os.path.abspath(root)
    output_path = args.output if args.output else _auto_output_name(root)
    pretty = not args.json_compact

    if args.verbose:
        print(f"Tome scanner\n{'=' * 40}\nScanning: {root}\n")

    # 1. Walk + inline parse
    if args.verbose:
        print("Step 1/5: Discovering files...")
    t0 = time.time()
    files = walk_directory(root, verbose=args.verbose)
    if args.verbose:
        print(f"  {len(files)} files in {time.time()-t0:.2f}s\n")
    if not files:
        print("No files found.", file=sys.stderr)
        sys.exit(1)

    # 2. Resolve imports
    if args.verbose:
        print("Step 2/5: Resolving imports...")
    t0 = time.time()
    edges, dead_imports = resolve_all_imports(files, verbose=args.verbose)
    if args.verbose:
        print(f"  {len(edges)} edges, {len(dead_imports)} dead in {time.time()-t0:.2f}s\n")

    # 3. Analyze
    if args.verbose:
        print("Step 3/5: Analyzing...")
    t0 = time.time()
    issues, runtime_edges, env_vars, entry_points, module_health = analyze(
        files, dead_imports, edges, verbose=args.verbose)
    if args.verbose:
        print(f"  Done in {time.time()-t0:.2f}s\n")

    # 4. Git
    if not args.no_git:
        if args.verbose:
            print("Step 4/5: Git analysis...")
        t0 = time.time()
        analyze_git(root, files, verbose=args.verbose)
        if args.verbose:
            print(f"  Done in {time.time()-t0:.2f}s\n")
    else:
        for f in files:
            f['git'] = None
        if args.verbose:
            print("Step 4/5: Git analysis skipped\n")

    # 5. Output
    if args.verbose:
        print("Step 5/5: Writing output...")
    data = format_output(root, files, edges, issues,
                         runtime_edges, env_vars, entry_points, module_health)

    # Diff
    if args.diff:
        diff = diff_scans(data, args.diff)
        if diff:
            data['diff'] = diff
        else:
            print(f"Warning: could not load previous scan '{args.diff}'", file=sys.stderr)

    write_output(data, output_path, pretty=pretty)

    # Summary
    m = data['metadata']
    print(f"Scan complete: {m['total_files']} files, {m['total_loc']} LOC, {m['total_modules']} modules")
    print(f"Output: {os.path.abspath(output_path)}")

    if args.summary:
        _print_summary(data)


if __name__ == '__main__':
    main()
