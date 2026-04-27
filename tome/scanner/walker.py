"""Directory traversal with inline parsing and .gitignore support."""

import fnmatch
import os

from config import (
    IGNORE_DIRS, BINARY_EXTENSIONS, MAX_FILE_SIZE, ENTRY_POINT_FILENAMES,
)
from tome.scanner.parsers import get_parser_for_extension


def parse_gitignore(root_path):
    """Parse root .gitignore and return (dir_patterns, file_patterns)."""
    path = os.path.join(root_path, '.gitignore')
    dir_patterns = []
    file_patterns = []
    if not os.path.isfile(path):
        return dir_patterns, file_patterns
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('!'):
                    continue
                if line.endswith('/'):
                    dir_patterns.append(line.rstrip('/'))
                else:
                    file_patterns.append(line)
    except (IOError, OSError):
        pass
    return dir_patterns, file_patterns


def _matches_gitignore(rel_path, patterns):
    """Check if rel_path matches any gitignore file pattern."""
    basename = os.path.basename(rel_path)
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(basename, pat):
            return True
    return False


def read_file_single_pass(filepath):
    """Single-pass read: binary check + decode in one I/O op.

    Returns (content_str, is_binary).  content_str is None when binary/unreadable.
    """
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
    except (IOError, OSError):
        return None, True

    if b'\x00' in raw[:8192]:
        return None, True

    for enc in ('utf-8', 'latin-1'):
        try:
            return raw.decode(enc), False
        except (UnicodeDecodeError, ValueError):
            continue
    return None, True


def walk_directory(root_path, verbose=False):
    """Walk directory tree, parse each file inline, discard raw content.

    Returns list of file-info dicts (without 'content' key).
    """
    root_path = os.path.abspath(root_path)
    files = []
    skipped = []

    gi_dirs, gi_files = parse_gitignore(root_path)
    ignore_dirs = IGNORE_DIRS | set(gi_dirs)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted(d for d in dirnames if d not in ignore_dirs)

        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_path).replace(os.sep, '/')

            if os.path.islink(filepath):
                skipped.append(rel_path)
                continue

            _, ext = os.path.splitext(filename)

            if ext.lower() in BINARY_EXTENSIONS:
                skipped.append(rel_path)
                continue

            if _matches_gitignore(rel_path, gi_files):
                skipped.append(rel_path)
                continue

            try:
                size = os.path.getsize(filepath)
            except OSError:
                skipped.append(rel_path)
                continue

            if size > MAX_FILE_SIZE:
                skipped.append(rel_path)
                continue

            # Single-pass I/O
            if size == 0:
                content = ""
                loc = 0
            else:
                content, is_bin = read_file_single_pass(filepath)
                if content is None:
                    skipped.append(rel_path)
                    continue
                loc = len(content.splitlines())

            # Module = containing directory
            parts = rel_path.split('/')
            parent = '/'.join(parts[:-1]) if len(parts) > 1 else ""
            module = parent if parent else "(root)"

            # --- Inline parsing (content discarded after this block) ----------
            parser = get_parser_for_extension(ext)
            if parser and content:
                raw_imports = parser.parse_imports(content, rel_path)
                exports = parser.parse_exports(content, rel_path)
                is_entry = parser.detect_entry_point(content, rel_path)
                runtime_refs = parser.detect_runtime_refs(content, rel_path)
                metrics = parser.compute_metrics(content, rel_path)
            else:
                raw_imports = []
                exports = []
                is_entry = False
                runtime_refs = []
                metrics = {
                    "loc": loc, "function_count": 0, "class_count": 0,
                    "cyclomatic_complexity": 0, "export_count": 0,
                }

            if filename in ENTRY_POINT_FILENAMES:
                is_entry = True
            # ------------------------------------------------------------------

            files.append({
                'path': rel_path,
                'name': filename,
                'parent': parent,
                'module': module,
                'extension': ext,
                'loc': loc,
                'size_bytes': size,
                'raw_imports': raw_imports,
                'exports': exports,
                'is_entry_point': is_entry,
                'runtime_refs': runtime_refs,
                'metrics': metrics,
            })

            if verbose:
                print(f"  [found] {rel_path} ({loc} lines)")

    if verbose:
        print(f"\nDiscovered {len(files)} files, skipped {len(skipped)}")

    return files
