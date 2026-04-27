"""AST-based Python parser implementing BaseParser.

Uses only the Python standard library.  Targets Python 3.8+.
"""

import ast
from typing import Any, Dict, List, Optional

from tome.scanner.parsers.base import BaseParser


class PythonParser(BaseParser):
    """Extracts imports, exports, entry-points, runtime refs and metrics
    from Python source files using the ``ast`` module."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_parse(content: str) -> Optional[ast.Module]:
        """Return an AST tree or *None* on syntax errors."""
        try:
            return ast.parse(content)
        except SyntaxError:
            return None

    @staticmethod
    def _annotate_parents(tree: ast.Module) -> None:
        """Set ``_parent`` on every node in *tree* so we can walk upward."""
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child._parent = node  # type: ignore[attr-defined]

    @staticmethod
    def _is_type_checking_if(node: ast.If) -> bool:
        """Return True when *node* is ``if TYPE_CHECKING:``."""
        test = node.test
        # Plain  ``if TYPE_CHECKING:``
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        # ``if typing.TYPE_CHECKING:``
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    @classmethod
    def _import_context(cls, node: ast.AST) -> str:
        """Walk up ``_parent`` links and return the import context string."""
        current = node
        context = "top_level"
        while True:
            parent = getattr(current, "_parent", None)
            if parent is None or isinstance(parent, ast.Module):
                break
            # Order matters: first matching rule wins, but we walk from the
            # import outward, so the *innermost* enclosing scope determines
            # the context.  We keep walking to find the most specific match
            # (closest to the import), but since we go inside-out the first
            # match is already the closest.
            if isinstance(parent, ast.If) and cls._is_type_checking_if(parent):
                return "type_only"
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return "lazy"
            if isinstance(parent, (ast.Try, ast.ExceptHandler)):
                return "conditional"
            # Python 3.11+  ``TryStar``
            if hasattr(ast, "TryStar") and isinstance(parent, ast.TryStar):
                return "conditional"
            if isinstance(parent, ast.If):
                return "conditional"
            current = parent
        return context

    @staticmethod
    def _reconstruct_import(node: ast.AST) -> str:
        """Rebuild a human-readable import statement."""
        if isinstance(node, ast.Import):
            parts = []
            for alias in node.names:
                if alias.asname:
                    parts.append(f"{alias.name} as {alias.asname}")
                else:
                    parts.append(alias.name)
            return "import " + ", ".join(parts)
        if isinstance(node, ast.ImportFrom):
            module = "." * (node.level or 0) + (node.module or "")
            parts = []
            for alias in node.names:
                if alias.asname:
                    parts.append(f"{alias.name} as {alias.asname}")
                else:
                    parts.append(alias.name)
            return f"from {module} import {', '.join(parts)}"
        return ""

    # ------------------------------------------------------------------
    # BaseParser implementation
    # ------------------------------------------------------------------

    def parse_imports(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        tree = self._safe_parse(content)
        if tree is None:
            return []

        self._annotate_parents(tree)
        results: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    results.append(
                        {
                            "module_path": None,
                            "imported_names": [alias.name],
                            "import_statement": self._reconstruct_import(node),
                            "line_number": node.lineno,
                            "context": self._import_context(node),
                            "_raw": {
                                "module": alias.name,
                                "level": 0,
                                "names": [alias.name],
                            },
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                results.append(
                    {
                        "module_path": None,
                        "imported_names": names,
                        "import_statement": self._reconstruct_import(node),
                        "line_number": node.lineno,
                        "context": self._import_context(node),
                        "_raw": {
                            "module": node.module,
                            "level": node.level or 0,
                            "names": names,
                        },
                    }
                )

        return results

    # ------------------------------------------------------------------

    def parse_exports(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        tree = self._safe_parse(content)
        if tree is None:
            return []

        # First pass — collect every top-level definition keyed by name so we
        # can look up line numbers when __all__ is present.
        definitions: Dict[str, Dict[str, Any]] = {}
        raw_exports: List[Dict[str, Any]] = []
        all_names: Optional[List[str]] = None

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                entry = {"name": node.name, "type": "class", "line_number": node.lineno}
                definitions[node.name] = entry
                raw_exports.append(entry)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry = {"name": node.name, "type": "function", "line_number": node.lineno}
                definitions[node.name] = entry
                raw_exports.append(entry)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Detect __all__
                        if name == "__all__" and isinstance(
                            node.value, (ast.List, ast.Tuple, ast.Set)
                        ):
                            all_names = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    all_names.append(elt.value)
                                # Python 3.8 compat: ast.Str
                                elif isinstance(elt, ast.Str):  # type: ignore[attr-defined]
                                    all_names.append(elt.s)  # type: ignore[attr-defined]
                            continue

                        # Skip private names
                        if name.startswith("_"):
                            continue

                        if name.isupper():
                            typ = "constant"
                        else:
                            typ = "variable"
                        entry = {"name": name, "type": typ, "line_number": node.lineno}
                        definitions[name] = entry
                        raw_exports.append(entry)

        # If __all__ was specified, filter to only those names.
        if all_names is not None:
            filtered: List[Dict[str, Any]] = []
            for name in all_names:
                if name in definitions:
                    filtered.append(definitions[name])
                else:
                    # Name in __all__ but no definition found — still list it.
                    filtered.append(
                        {"name": name, "type": "variable", "line_number": 0}
                    )
            return filtered

        return raw_exports

    # ------------------------------------------------------------------

    def detect_entry_point(self, content: str, file_path: str) -> bool:
        tree = self._safe_parse(content)
        if tree is None:
            return False

        for node in tree.body:
            # Pattern 1: if __name__ == '__main__':
            if isinstance(node, ast.If):
                if self._is_main_guard(node):
                    return True

            # Pattern 2: app = FastAPI() / app = Flask(...)
            if isinstance(node, ast.Assign):
                if self._is_framework_app(node):
                    return True

        # Pattern 3: uvicorn.run() anywhere
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._is_uvicorn_run(node):
                    return True

        return False

    @staticmethod
    def _is_main_guard(node: ast.If) -> bool:
        """Check ``if __name__ == '__main__':``."""
        test = node.test
        if not isinstance(test, ast.Compare):
            return False
        if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
            return False
        for comparator in test.comparators:
            if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                return True
            # Python 3.8 compat
            if isinstance(comparator, ast.Str) and comparator.s == "__main__":  # type: ignore[attr-defined]
                return True
        return False

    @staticmethod
    def _is_framework_app(node: ast.Assign) -> bool:
        """Check ``app = FastAPI()`` or ``app = Flask(...)``."""
        if not isinstance(node.value, ast.Call):
            return False
        func = node.value.func
        framework_names = {"FastAPI", "Flask"}
        if isinstance(func, ast.Name) and func.id in framework_names:
            return True
        if isinstance(func, ast.Attribute) and func.attr in framework_names:
            return True
        return False

    @staticmethod
    def _is_uvicorn_run(node: ast.Call) -> bool:
        """Check ``uvicorn.run(...)``."""
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "run":
            if isinstance(func.value, ast.Name) and func.value.id == "uvicorn":
                return True
        return False

    # ------------------------------------------------------------------

    def detect_runtime_refs(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        tree = self._safe_parse(content)
        if tree is None:
            return []

        self._annotate_parents(tree)
        results: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            # --- Decorators on functions (HTTP routes) ---
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    ref = self._check_route_decorator(dec, node.lineno)
                    if ref is not None:
                        results.append(ref)

            if not isinstance(node, ast.Call):
                continue

            # 1. open('path')
            ref = self._check_open_call(node)
            if ref is not None:
                results.append(ref)
                continue

            # 2. os.getenv('KEY')
            ref = self._check_os_getenv(node)
            if ref is not None:
                results.append(ref)
                continue

            # 3. os.environ.get('KEY')
            ref = self._check_os_environ_get(node)
            if ref is not None:
                results.append(ref)
                continue

            # 4. load_dotenv()
            ref = self._check_load_dotenv(node)
            if ref is not None:
                results.append(ref)
                continue

            # 5. yaml.safe_load / toml.load / json.load
            ref = self._check_config_load(node)
            if ref is not None:
                results.append(ref)
                continue

        # 3b. os.environ['KEY'] (Subscript, not a Call)
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                ref = self._check_os_environ_subscript(node)
                if ref is not None:
                    results.append(ref)

        return results

    # --- runtime-ref helpers ---

    @staticmethod
    def _first_str_arg(node: ast.Call) -> Optional[str]:
        """Return the first positional argument if it is a string constant."""
        if node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
            if isinstance(arg, ast.Str):  # type: ignore[attr-defined]
                return arg.s  # type: ignore[attr-defined]
        return None

    @classmethod
    def _check_open_call(cls, node: ast.Call) -> Optional[Dict[str, Any]]:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            target = cls._first_str_arg(node)
            if target is not None:
                return {
                    "target": target,
                    "type": "file_read",
                    "line_number": node.lineno,
                    "statement": f"open('{target}')",
                }
        return None

    @classmethod
    def _check_os_getenv(cls, node: ast.Call) -> Optional[Dict[str, Any]]:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        ):
            target = cls._first_str_arg(node)
            if target is not None:
                return {
                    "target": target,
                    "type": "env_var",
                    "line_number": node.lineno,
                    "statement": f"os.getenv('{target}')",
                }
        return None

    @classmethod
    def _check_os_environ_get(cls, node: ast.Call) -> Optional[Dict[str, Any]]:
        """``os.environ.get('KEY')``."""
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "environ"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "os"
        ):
            target = cls._first_str_arg(node)
            if target is not None:
                return {
                    "target": target,
                    "type": "env_var",
                    "line_number": node.lineno,
                    "statement": f"os.environ.get('{target}')",
                }
        return None

    @staticmethod
    def _check_os_environ_subscript(node: ast.Subscript) -> Optional[Dict[str, Any]]:
        """``os.environ['KEY']``."""
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "environ"
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
        ):
            # The subscript key — Python 3.9+ uses node.slice directly,
            # Python 3.8 wraps it in an Index node.
            sl = node.slice
            if isinstance(sl, ast.Index):  # type: ignore[attr-defined]
                sl = sl.value  # type: ignore[attr-defined]
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                return {
                    "target": sl.value,
                    "type": "env_var",
                    "line_number": node.lineno,
                    "statement": f"os.environ['{sl.value}']",
                }
            if isinstance(sl, ast.Str):  # type: ignore[attr-defined]
                return {
                    "target": sl.s,  # type: ignore[attr-defined]
                    "type": "env_var",
                    "line_number": node.lineno,
                    "statement": f"os.environ['{sl.s}']",  # type: ignore[attr-defined]
                }
        return None

    @staticmethod
    def _check_load_dotenv(node: ast.Call) -> Optional[Dict[str, Any]]:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "load_dotenv":
            return {
                "target": ".env",
                "type": "config_load",
                "line_number": node.lineno,
                "statement": "load_dotenv()",
            }
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "load_dotenv"
        ):
            return {
                "target": ".env",
                "type": "config_load",
                "line_number": node.lineno,
                "statement": "load_dotenv()",
            }
        return None

    @classmethod
    def _check_config_load(cls, node: ast.Call) -> Optional[Dict[str, Any]]:
        """``yaml.safe_load(...)``, ``toml.load(...)``, ``json.load(...)``."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None

        # yaml.safe_load / yaml.load
        if (
            func.attr in ("safe_load", "load")
            and isinstance(func.value, ast.Name)
            and func.value.id == "yaml"
        ):
            target = cls._first_str_arg(node) or "yaml_config"
            return {
                "target": target,
                "type": "config_load",
                "line_number": node.lineno,
                "statement": f"yaml.{func.attr}(...)",
            }

        # toml.load
        if (
            func.attr == "load"
            and isinstance(func.value, ast.Name)
            and func.value.id == "toml"
        ):
            target = cls._first_str_arg(node) or "toml_config"
            return {
                "target": target,
                "type": "config_load",
                "line_number": node.lineno,
                "statement": "toml.load(...)",
            }

        # json.load
        if (
            func.attr == "load"
            and isinstance(func.value, ast.Name)
            and func.value.id == "json"
        ):
            # Try to get filename from open() inside: json.load(open('x'))
            target = "json_config"
            if node.args:
                inner = node.args[0]
                if isinstance(inner, ast.Call):
                    inner_target = cls._first_str_arg(inner)
                    if inner_target is not None:
                        target = inner_target
            return {
                "target": target,
                "type": "config_load",
                "line_number": node.lineno,
                "statement": "json.load(...)",
            }

        return None

    @staticmethod
    def _check_route_decorator(
        dec: ast.AST, func_lineno: int
    ) -> Optional[Dict[str, Any]]:
        """Check if *dec* is a route decorator like ``@app.get('/path')``."""
        route_attrs = {
            "get", "post", "put", "delete", "patch",
            "route", "api_route", "websocket",
        }
        if not isinstance(dec, ast.Call):
            return None
        func = dec.func
        if isinstance(func, ast.Attribute) and func.attr in route_attrs:
            # First positional string argument is the route path.
            if dec.args:
                arg = dec.args[0]
                path: Optional[str] = None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    path = arg.value
                elif isinstance(arg, ast.Str):  # type: ignore[attr-defined]
                    path = arg.s  # type: ignore[attr-defined]
                if path is not None:
                    return {
                        "target": path,
                        "type": "http_server",
                        "line_number": dec.lineno,
                        "statement": f"@...{func.attr}('{path}')",
                    }
        return None

    # ------------------------------------------------------------------

    def compute_metrics(self, content: str, file_path: str) -> Dict[str, Any]:
        tree = self._safe_parse(content)
        if tree is None:
            return {
                "loc": 0,
                "function_count": 0,
                "class_count": 0,
                "cyclomatic_complexity": 0,
                "export_count": 0,
            }

        function_count = 0
        class_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1

        # Cyclomatic complexity
        if function_count > 0:
            complexity = self._total_function_complexity(tree)
        else:
            # Module-level complexity
            complexity = self._body_complexity(tree.body)

        loc = len(content.splitlines())
        export_count = len(self.parse_exports(content, file_path))

        return {
            "loc": loc,
            "function_count": function_count,
            "class_count": class_count,
            "cyclomatic_complexity": complexity,
            "export_count": export_count,
        }

    @classmethod
    def _total_function_complexity(cls, tree: ast.Module) -> int:
        """Sum complexity over all FunctionDef / AsyncFunctionDef nodes."""
        total = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total += 1 + cls._body_complexity(node.body)
        return total

    @classmethod
    def _body_complexity(cls, body: list) -> int:
        """Count decision points in a list of AST statements (recursively)."""
        count = 0
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                count += 1
            elif isinstance(node, ast.ExceptHandler):
                count += 1
            elif isinstance(node, ast.Assert):
                count += 1
            elif isinstance(node, ast.BoolOp):
                # `a and b and c` has values length 3 -> 2 operators
                count += len(node.values) - 1
        return count
