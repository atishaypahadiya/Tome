"""Compare two Tome scan outputs and produce a diff report.

Compares a current in-memory scan dict against a previous scan loaded from
a JSON file on disk.  Only Python standard library is used.
"""

import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple


def _file_path_set(files: List[Dict[str, Any]]) -> Set[str]:
    """Extract the set of file paths from a files list."""
    return {f["path"] for f in files}


def _file_loc_map(files: List[Dict[str, Any]]) -> Dict[str, int]:
    """Build a mapping of path -> loc from a files list."""
    return {f["path"]: f.get("loc", 0) for f in files}


def _edge_set(edges: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """Build a set of (from, to) tuples from an edges list."""
    return {(e["from"], e["to"]) for e in edges}


def _edge_type_map(edges: List[Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    """Build a mapping of (from, to) -> type from an edges list."""
    return {(e["from"], e["to"]): e.get("type", "unknown") for e in edges}


def _module_name_set(modules: List[Dict[str, Any]]) -> Set[str]:
    """Extract the set of module names from a modules list."""
    return {m["name"] for m in modules}


def _module_map(modules: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a mapping of name -> module dict from a modules list."""
    return {m["name"]: m for m in modules}


def _orphan_set(issues: Dict[str, Any]) -> Set[str]:
    """Extract the set of orphan file paths from issues."""
    return set(issues.get("orphans", []))


def _dead_import_set(
    issues: Dict[str, Any],
) -> Set[Tuple[str, str]]:
    """Extract a set of (file, imports) tuples from dead_imports in issues.

    The 'imports' value is converted to a string so it can be placed in a set.
    When dead_imports entries have a list of import targets we join them with a
    comma for a stable, hashable representation.
    """
    result: Set[Tuple[str, str]] = set()
    for entry in issues.get("dead_imports", []):
        file_path = entry.get("file", "")
        imports_val = entry.get("imports", "")
        if isinstance(imports_val, list):
            imports_str = ",".join(sorted(imports_val))
        else:
            imports_str = str(imports_val)
        result.add((file_path, imports_str))
    return result


def _dead_import_list_from_set(
    di_set: Set[Tuple[str, str]],
) -> List[Dict[str, str]]:
    """Convert a dead-import set back to a list of dicts for the report."""
    result = []
    for file_path, imports_str in sorted(di_set):
        result.append({"file": file_path, "imports": imports_str})
    return result


def diff_scans(
    current_data: Dict[str, Any], previous_path: str
) -> Optional[Dict[str, Any]]:
    """Compare *current_data* (in memory) with a previous scan on disk.

    Parameters
    ----------
    current_data:
        The current scan output dict (as produced by ``format_output``).
    previous_path:
        Filesystem path to the previous scan JSON file.

    Returns
    -------
    dict or None
        A structured diff report, or ``None`` if the previous file cannot be
        loaded (missing, unreadable, or malformed JSON).
    """
    # ------------------------------------------------------------------
    # 1. Load previous scan
    # ------------------------------------------------------------------
    try:
        with open(previous_path, "r", encoding="utf-8") as fh:
            previous_data: Dict[str, Any] = json.load(fh)
    except (OSError, IOError, json.JSONDecodeError, TypeError, ValueError):
        return None

    # ------------------------------------------------------------------
    # 2. Extract sub-structures with safe defaults
    # ------------------------------------------------------------------
    cur_files: List[Dict[str, Any]] = current_data.get("files", [])
    prev_files: List[Dict[str, Any]] = previous_data.get("files", [])

    cur_edges: List[Dict[str, Any]] = current_data.get("edges", [])
    prev_edges: List[Dict[str, Any]] = previous_data.get("edges", [])

    cur_modules: List[Dict[str, Any]] = current_data.get("modules", [])
    prev_modules: List[Dict[str, Any]] = previous_data.get("modules", [])

    cur_issues: Dict[str, Any] = current_data.get("issues", {})
    prev_issues: Dict[str, Any] = previous_data.get("issues", {})

    cur_meta: Dict[str, Any] = current_data.get("metadata", {})
    prev_meta: Dict[str, Any] = previous_data.get("metadata", {})

    # ------------------------------------------------------------------
    # 3. File comparison
    # ------------------------------------------------------------------
    cur_paths = _file_path_set(cur_files)
    prev_paths = _file_path_set(prev_files)

    added_paths = sorted(cur_paths - prev_paths)
    removed_paths = sorted(prev_paths - cur_paths)

    cur_loc_map = _file_loc_map(cur_files)
    prev_loc_map = _file_loc_map(prev_files)

    common_paths = cur_paths & prev_paths
    files_modified: List[Dict[str, Any]] = []
    for p in sorted(common_paths):
        loc_before = prev_loc_map.get(p, 0)
        loc_after = cur_loc_map.get(p, 0)
        if loc_before != loc_after:
            files_modified.append(
                {
                    "path": p,
                    "loc_before": loc_before,
                    "loc_after": loc_after,
                    "delta": loc_after - loc_before,
                }
            )

    # ------------------------------------------------------------------
    # 4. Edge comparison
    # ------------------------------------------------------------------
    cur_edge_set = _edge_set(cur_edges)
    prev_edge_set = _edge_set(prev_edges)

    cur_edge_types = _edge_type_map(cur_edges)
    prev_edge_types = _edge_type_map(prev_edges)

    edges_added: List[Dict[str, str]] = []
    for key in sorted(cur_edge_set - prev_edge_set):
        edges_added.append(
            {"from": key[0], "to": key[1], "type": cur_edge_types.get(key, "unknown")}
        )

    edges_removed: List[Dict[str, str]] = []
    for key in sorted(prev_edge_set - cur_edge_set):
        edges_removed.append(
            {
                "from": key[0],
                "to": key[1],
                "type": prev_edge_types.get(key, "unknown"),
            }
        )

    # ------------------------------------------------------------------
    # 5. Module comparison
    # ------------------------------------------------------------------
    cur_mod_names = _module_name_set(cur_modules)
    prev_mod_names = _module_name_set(prev_modules)

    modules_added_names = sorted(cur_mod_names - prev_mod_names)
    modules_removed_names = sorted(prev_mod_names - cur_mod_names)

    cur_mod_map = _module_map(cur_modules)
    prev_mod_map = _module_map(prev_modules)

    module_deltas: List[Dict[str, Any]] = []
    for name in sorted(cur_mod_names & prev_mod_names):
        cm = cur_mod_map[name]
        pm = prev_mod_map[name]
        loc_before = pm.get("total_loc", 0)
        loc_after = cm.get("total_loc", 0)
        files_before = pm.get("file_count", 0)
        files_after = cm.get("file_count", 0)
        if loc_before != loc_after or files_before != files_after:
            module_deltas.append(
                {
                    "name": name,
                    "loc_before": loc_before,
                    "loc_after": loc_after,
                    "files_before": files_before,
                    "files_after": files_after,
                }
            )

    # ------------------------------------------------------------------
    # 6. Issue comparison (orphans & dead imports)
    # ------------------------------------------------------------------
    cur_orphans = _orphan_set(cur_issues)
    prev_orphans = _orphan_set(prev_issues)

    orphans_resolved = sorted(prev_orphans - cur_orphans)
    new_orphans = sorted(cur_orphans - prev_orphans)

    cur_dead = _dead_import_set(cur_issues)
    prev_dead = _dead_import_set(prev_issues)

    dead_imports_resolved = _dead_import_list_from_set(prev_dead - cur_dead)
    new_dead_imports = _dead_import_list_from_set(cur_dead - prev_dead)

    # ------------------------------------------------------------------
    # 7. LOC delta
    # ------------------------------------------------------------------
    loc_delta = cur_meta.get("total_loc", 0) - prev_meta.get("total_loc", 0)

    # ------------------------------------------------------------------
    # 8. Assemble diff report
    # ------------------------------------------------------------------
    return {
        "compared_to": os.path.basename(previous_path),
        "previous_timestamp": prev_meta.get("timestamp", ""),
        "summary": {
            "files_added": len(added_paths),
            "files_removed": len(removed_paths),
            "files_modified": len(files_modified),
            "edges_added": len(edges_added),
            "edges_removed": len(edges_removed),
            "loc_delta": loc_delta,
            "modules_added": len(modules_added_names),
            "modules_removed": len(modules_removed_names),
        },
        "files_added": added_paths,
        "files_removed": removed_paths,
        "files_modified": files_modified,
        "edges_added": edges_added,
        "edges_removed": edges_removed,
        "issues_resolved": {
            "orphans_resolved": orphans_resolved,
            "dead_imports_resolved": dead_imports_resolved,
        },
        "issues_introduced": {
            "new_orphans": new_orphans,
            "new_dead_imports": new_dead_imports,
        },
        "module_deltas": module_deltas,
    }
