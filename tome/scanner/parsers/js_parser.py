"""Regex-based JavaScript/TypeScript parser.

Implements all methods from BaseParser using only the Python standard library.
Targets Python 3.8+.
"""

import os
import re

from tome.scanner.parsers.base import BaseParser

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# --- Import patterns -------------------------------------------------------

# ES6 static: import <clause> from '<module>'
_RE_ES6_IMPORT = re.compile(
    r"""^[ \t]*import\s+"""           # leading import keyword
    r"""(.+?)\s+from\s+"""            # group 1: import clause
    r"""['"]([^'"]+)['"]""",          # group 2: module path
    re.MULTILINE,
)

# Side-effect import: import '<module>'  (no clause, just the string)
_RE_SIDE_EFFECT_IMPORT = re.compile(
    r"""^[ \t]*import\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)

# CommonJS require: require('<module>')
_RE_REQUIRE = re.compile(
    r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# Dynamic import: import('<module>')
# Must NOT match the static `import <names> from ...` form.
# We look for `import(` that is NOT preceded by word characters (avoids
# matching inside identifiers), and capture the string argument.
_RE_DYNAMIC_IMPORT = re.compile(
    r"""(?<!\w)import\s*\(\s*['"]([^'"]+)['"]\s*\)""",
)

# --- Export patterns -------------------------------------------------------

_RE_EXPORT_FUNCTION = re.compile(
    r"""^[ \t]*export\s+(?:async\s+)?function\s+(\w+)""",
    re.MULTILINE,
)

_RE_EXPORT_CLASS = re.compile(
    r"""^[ \t]*export\s+class\s+(\w+)""",
    re.MULTILINE,
)

_RE_EXPORT_CONST = re.compile(
    r"""^[ \t]*export\s+const\s+(\w+)""",
    re.MULTILINE,
)

_RE_EXPORT_LET_VAR = re.compile(
    r"""^[ \t]*export\s+(?:let|var)\s+(\w+)""",
    re.MULTILINE,
)

# export default function Name / export default class Name
_RE_EXPORT_DEFAULT_NAMED = re.compile(
    r"""^[ \t]*export\s+default\s+(?:(?:async\s+)?function|class)\s+(\w+)""",
    re.MULTILINE,
)

# export default <anything else>  (anonymous default)
_RE_EXPORT_DEFAULT_ANON = re.compile(
    r"""^[ \t]*export\s+default\s+""",
    re.MULTILINE,
)

# module.exports.NAME = ...
_RE_MODULE_EXPORTS_NAMED = re.compile(
    r"""^[ \t]*module\.exports\.(\w+)\s*=""",
    re.MULTILINE,
)

# module.exports = ...
_RE_MODULE_EXPORTS = re.compile(
    r"""^[ \t]*module\.exports\s*=""",
    re.MULTILINE,
)

# export { A, B, C }  — named re-exports / barrel exports
_RE_EXPORT_BRACES = re.compile(
    r"""^[ \t]*export\s*\{([^}]+)\}""",
    re.MULTILINE,
)

# --- Runtime ref patterns --------------------------------------------------

_RE_FETCH = re.compile(
    r"""\bfetch\s*\(\s*['"]([^'"]+)['"]\s*""",
)

_RE_AXIOS = re.compile(
    r"""\baxios\.(?:get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]\s*""",
)

_RE_REQUIRE_JSON = re.compile(
    r"""\brequire\s*\(\s*['"]([^'"]*\.json)['"]\s*\)""",
)

_RE_FS_READ = re.compile(
    r"""\bfs\.(?:readFileSync|readFile)\s*\(\s*['"]([^'"]+)['"]\s*""",
)

_RE_PROCESS_ENV = re.compile(
    r"""\bprocess\.env\.([A-Za-z_][A-Za-z0-9_]*)""",
)

# --- Metric patterns -------------------------------------------------------

_RE_FUNCTION_DEF = re.compile(
    r"""^\s*(?:export\s+)?(?:async\s+)?function\s""",
    re.MULTILINE,
)

_RE_ARROW_BODY = re.compile(r"""=>\s*\{""")

_RE_CLASS_DEF = re.compile(
    r"""^\s*(?:export\s+)?(?:default\s+)?class\s""",
    re.MULTILINE,
)

# Cyclomatic complexity tokens
_RE_CC_IF = re.compile(r"""\bif\b""")
_RE_CC_ELSE_IF = re.compile(r"""\belse\s+if\b""")
_RE_CC_FOR = re.compile(r"""\bfor\b""")
_RE_CC_WHILE = re.compile(r"""\bwhile\b""")
_RE_CC_CATCH = re.compile(r"""\bcatch\b""")
_RE_CC_CASE = re.compile(r"""\bcase\b""")
_RE_CC_AND = re.compile(r"""&&""")
_RE_CC_OR = re.compile(r"""\|\|""")
# Ternary `?` — but NOT optional-chaining `?.`
_RE_CC_TERNARY = re.compile(r"""\?(?!\.)""")

# --- Entry-point patterns --------------------------------------------------

_RE_APP_LISTEN = re.compile(r"""\bapp\.listen\s*\(""")
_RE_CREATE_SERVER = re.compile(r"""\bcreateServer\s*\(""")
_RE_DOM_READY = re.compile(
    r"""addEventListener\s*\(\s*['"]DOMContentLoaded['"]\s*"""
)

_ENTRY_BASENAMES = frozenset({
    "main.js", "index.js", "app.js",
    "main.ts", "index.ts", "app.ts",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_import_clause(clause):
    """Parse the clause between ``import`` and ``from`` into a list of names.

    Examples
    --------
    - ``Foo``                -> ["Foo"]
    - ``{ A, B }``           -> ["A", "B"]
    - ``{ A as X, B }``      -> ["A", "B"]   (original names)
    - ``* as Foo``           -> ["*"]
    - ``Foo, { A, B }``     -> ["Foo", "A", "B"]
    - ``Foo, * as Bar``     -> ["Foo", "*"]
    """
    clause = clause.strip()
    if not clause:
        return []

    names = []  # type: list[str]

    # Handle braces portion: { A as X, B }
    brace_match = re.search(r"\{([^}]*)\}", clause)
    if brace_match:
        inner = brace_match.group(1)
        for item in inner.split(","):
            item = item.strip()
            if not item:
                continue
            # ``A as X`` -> take the original name ``A``
            parts = item.split()
            if parts:
                names.append(parts[0])
        # Remove the braces portion from clause to process the rest
        clause = clause[: brace_match.start()] + clause[brace_match.end():]

    # Handle namespace: * as Foo
    star_match = re.search(r"\*\s+as\s+\w+", clause)
    if star_match:
        names.append("*")
        clause = clause[: star_match.start()] + clause[star_match.end():]

    # Remaining tokens are default imports (e.g. ``Foo`` in ``import Foo, { A } from ...``)
    for token in clause.split(","):
        token = token.strip()
        if token and re.match(r"^[A-Za-z_$][\w$]*$", token):
            names.append(token)

    return names if names else ["*"]  # fallback


def _line_number_of_offset(content, offset):
    """Return 1-based line number for a character offset."""
    return content.count("\n", 0, offset) + 1


def _build_brace_depth_map(lines):
    """Return a list where index *i* gives the brace depth at the START of line *i*.

    Also return a companion list ``in_try`` where ``in_try[i]`` is True when
    that line is inside a try block (very rough heuristic).
    """
    depth = 0
    depths = []  # type: list[int]
    in_try_flags = []  # type: list[bool]
    try_depth = -1  # depth at which a try block was opened; -1 = not in try

    for line in lines:
        depths.append(depth)

        # Detect ``try {`` on this line (may span tokens, but simple heuristic)
        if re.search(r"\btry\s*\{", line):
            try_depth = depth  # depth before the opening brace

        opens = line.count("{")
        closes = line.count("}")
        depth += opens - closes

        # If we have dropped back to or below the try-start depth, try block ended.
        if try_depth >= 0 and depth <= try_depth:
            try_depth = -1

        in_try_flags.append(try_depth >= 0)

    return depths, in_try_flags


def _determine_context_for_require(line_idx, depths, in_try_flags):
    """Determine context for a ``require()`` call at *line_idx*."""
    if in_try_flags[line_idx]:
        return "conditional"
    if depths[line_idx] > 0:
        return "lazy"
    return "top_level"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class JSParser(BaseParser):
    """JavaScript / TypeScript parser backed by regular expressions."""

    # ---- parse_imports ----------------------------------------------------

    def parse_imports(self, content, file_path):
        """Return a list of ImportInfo dicts extracted from *content*."""
        if not content:
            return []

        results = []  # type: list[dict]
        lines = content.splitlines()
        depths, in_try_flags = _build_brace_depth_map(lines)

        # Track which offsets we've already matched so that side-effect regex
        # doesn't double-match ES6 imports and dynamic import regex doesn't
        # match static imports.
        matched_offsets = set()  # type: set[int]

        # 1. ES6 static imports  -----------------------------------------------
        for m in _RE_ES6_IMPORT.finditer(content):
            matched_offsets.add(m.start())
            clause = m.group(1)
            raw_path = m.group(2)
            imported_names = _parse_import_clause(clause)
            lineno = _line_number_of_offset(content, m.start())
            line_idx = lineno - 1

            if line_idx < len(depths):
                ctx = "top_level" if depths[line_idx] == 0 else "lazy"
            else:
                ctx = "top_level"

            results.append({
                "module_path": None,
                "imported_names": imported_names,
                "import_statement": m.group(0).strip(),
                "line_number": lineno,
                "context": ctx,
                "_raw": {"raw_path": raw_path, "kind": "import"},
            })

        # 2. Side-effect imports  -----------------------------------------------
        for m in _RE_SIDE_EFFECT_IMPORT.finditer(content):
            if m.start() in matched_offsets:
                continue
            raw_path = m.group(1)
            lineno = _line_number_of_offset(content, m.start())
            line_idx = lineno - 1

            if line_idx < len(depths):
                ctx = "top_level" if depths[line_idx] == 0 else "lazy"
            else:
                ctx = "top_level"

            matched_offsets.add(m.start())
            results.append({
                "module_path": None,
                "imported_names": [],
                "import_statement": m.group(0).strip(),
                "line_number": lineno,
                "context": ctx,
                "_raw": {"raw_path": raw_path, "kind": "import"},
            })

        # 3. Dynamic imports  ---------------------------------------------------
        for m in _RE_DYNAMIC_IMPORT.finditer(content):
            # Skip if this offset was already captured as an ES6 / side-effect import
            if m.start() in matched_offsets:
                continue

            # Also skip if this position is part of a line already captured by
            # the ES6 static regex (the static regex anchors at start of line,
            # so the dynamic regex may match mid-line inside a static import).
            lineno = _line_number_of_offset(content, m.start())
            line_idx = lineno - 1
            already_captured = False
            for off in matched_offsets:
                if _line_number_of_offset(content, off) == lineno:
                    already_captured = True
                    break
            if already_captured:
                continue

            raw_path = m.group(1)

            results.append({
                "module_path": None,
                "imported_names": [],
                "import_statement": m.group(0).strip(),
                "line_number": lineno,
                "context": "lazy",
                "_raw": {"raw_path": raw_path, "kind": "dynamic_import"},
            })

        # 4. CommonJS require  --------------------------------------------------
        for m in _RE_REQUIRE.finditer(content):
            # Skip requires that were already picked up as dynamic import JSON
            # or inside an import line captured above.
            lineno = _line_number_of_offset(content, m.start())
            line_idx = lineno - 1

            already_captured = False
            for off in matched_offsets:
                if _line_number_of_offset(content, off) == lineno:
                    already_captured = True
                    break
            if already_captured:
                continue

            raw_path = m.group(1)

            if line_idx < len(depths):
                ctx = _determine_context_for_require(line_idx, depths, in_try_flags)
            else:
                ctx = "top_level"

            results.append({
                "module_path": None,
                "imported_names": [],
                "import_statement": m.group(0).strip(),
                "line_number": lineno,
                "context": ctx,
                "_raw": {"raw_path": raw_path, "kind": "require"},
            })

        return results

    # ---- parse_exports ----------------------------------------------------

    def parse_exports(self, content, file_path):
        """Return a list of ExportInfo dicts extracted from *content*."""
        if not content:
            return []

        results = []  # type: list[dict]
        seen_lines = set()  # type: set[int]

        def _add(name, etype, lineno):
            if lineno not in seen_lines:
                seen_lines.add(lineno)
                results.append({
                    "name": name,
                    "type": etype,
                    "line_number": lineno,
                })

        # export default function Name / export default class Name
        for m in _RE_EXPORT_DEFAULT_NAMED.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "function" if "function" in m.group(0) else "class", lineno)

        # export function Name
        for m in _RE_EXPORT_FUNCTION.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "function", lineno)

        # export class Name
        for m in _RE_EXPORT_CLASS.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "class", lineno)

        # export const Name
        for m in _RE_EXPORT_CONST.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "constant", lineno)

        # export let / export var Name
        for m in _RE_EXPORT_LET_VAR.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "variable", lineno)

        # export default <anonymous>
        for m in _RE_EXPORT_DEFAULT_ANON.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            # Skip if this line was already captured as a named default export
            if lineno in seen_lines:
                continue
            _add("default", "variable", lineno)

        # module.exports.NAME = ...
        for m in _RE_MODULE_EXPORTS_NAMED.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            _add(m.group(1), "variable", lineno)

        # module.exports = ...
        for m in _RE_MODULE_EXPORTS.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            # Don't double-count module.exports.NAME lines
            if lineno in seen_lines:
                continue
            _add("default", "variable", lineno)

        # export { A, B, C }
        for m in _RE_EXPORT_BRACES.finditer(content):
            lineno = _line_number_of_offset(content, m.start())
            inner = m.group(1)
            for item in inner.split(","):
                item = item.strip()
                if not item:
                    continue
                # Handle ``A as B`` — export the *alias* (B), which is the
                # public name consumers see.
                parts = item.split()
                if len(parts) >= 3 and parts[1] == "as":
                    name = parts[2]
                else:
                    name = parts[0] if parts else item
                results.append({
                    "name": name,
                    "type": "variable",
                    "line_number": lineno,
                })

        return results

    # ---- detect_entry_point -----------------------------------------------

    def detect_entry_point(self, content, file_path):
        """Return True if *content* / *file_path* looks like an entry point."""
        if not content:
            basename = os.path.basename(file_path) if file_path else ""
            return basename in _ENTRY_BASENAMES

        if _RE_APP_LISTEN.search(content):
            return True
        if _RE_CREATE_SERVER.search(content):
            return True
        if _RE_DOM_READY.search(content):
            return True

        basename = os.path.basename(file_path) if file_path else ""
        if basename in _ENTRY_BASENAMES:
            return True

        return False

    # ---- detect_runtime_refs ----------------------------------------------

    def detect_runtime_refs(self, content, file_path):
        """Return a list of RuntimeRef dicts found in *content*."""
        if not content:
            return []

        results = []  # type: list[dict]

        for lineno, line in enumerate(content.splitlines(), start=1):
            # fetch() with URL
            for m in _RE_FETCH.finditer(line):
                url = m.group(1)
                if url.startswith("/") or url.startswith("http"):
                    results.append({
                        "target": url,
                        "type": "http_client",
                        "line_number": lineno,
                        "statement": line.strip(),
                    })

            # axios.<method>()
            for m in _RE_AXIOS.finditer(line):
                results.append({
                    "target": m.group(1),
                    "type": "http_client",
                    "line_number": lineno,
                    "statement": line.strip(),
                })

            # require('...json')
            for m in _RE_REQUIRE_JSON.finditer(line):
                results.append({
                    "target": m.group(1),
                    "type": "config_load",
                    "line_number": lineno,
                    "statement": line.strip(),
                })

            # fs.readFileSync / fs.readFile
            for m in _RE_FS_READ.finditer(line):
                results.append({
                    "target": m.group(1),
                    "type": "file_read",
                    "line_number": lineno,
                    "statement": line.strip(),
                })

            # process.env.VAR
            for m in _RE_PROCESS_ENV.finditer(line):
                results.append({
                    "target": m.group(1),
                    "type": "env_var",
                    "line_number": lineno,
                    "statement": line.strip(),
                })

        return results

    # ---- compute_metrics --------------------------------------------------

    def compute_metrics(self, content, file_path):
        """Return a FileMetrics dict for *content*."""
        if not content:
            return {
                "loc": 0,
                "function_count": 0,
                "class_count": 0,
                "cyclomatic_complexity": 1,
                "export_count": 0,
            }

        loc = len(content.splitlines())

        function_count = (
            len(_RE_FUNCTION_DEF.findall(content))
            + len(_RE_ARROW_BODY.findall(content))
        )

        class_count = len(_RE_CLASS_DEF.findall(content))

        # Cyclomatic complexity: base 1 + decision points
        cc = 1
        # Count ``else if`` first so we can subtract from standalone ``if`` count.
        else_if_count = len(_RE_CC_ELSE_IF.findall(content))
        if_count = len(_RE_CC_IF.findall(content))
        # Each ``if`` match also matches the ``if`` in ``else if``, so the net
        # standalone-if count is ``if_count - else_if_count``.  But both
        # standalone-if and else-if are decision points, so we add them all.
        cc += if_count  # includes else-if occurrences
        cc += len(_RE_CC_FOR.findall(content))
        cc += len(_RE_CC_WHILE.findall(content))
        cc += len(_RE_CC_CATCH.findall(content))
        cc += len(_RE_CC_CASE.findall(content))
        cc += len(_RE_CC_AND.findall(content))
        cc += len(_RE_CC_OR.findall(content))
        cc += len(_RE_CC_TERNARY.findall(content))

        export_count = len(self.parse_exports(content, file_path))

        return {
            "loc": loc,
            "function_count": function_count,
            "class_count": class_count,
            "cyclomatic_complexity": cc,
            "export_count": export_count,
        }
