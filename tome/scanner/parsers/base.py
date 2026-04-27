"""Abstract base class for language parsers."""

import abc


class BaseParser(abc.ABC):
    """Interface every language parser must implement."""

    @abc.abstractmethod
    def parse_imports(self, content, file_path):
        """Return list of ImportInfo dicts.

        Each dict has keys:
            module_path (str|None) — resolved later, raw module ref for now
            imported_names (list[str])
            import_statement (str)
            line_number (int)
            context: "top_level" | "lazy" | "conditional" | "type_only"
            _raw — parser-specific raw data for resolution
        """

    @abc.abstractmethod
    def parse_exports(self, content, file_path):
        """Return list of ExportInfo dicts.

        Each dict: {name, type ("function"|"class"|"variable"|"constant"), line_number}
        """

    @abc.abstractmethod
    def detect_entry_point(self, content, file_path):
        """Return True if this file looks like an entry point."""

    @abc.abstractmethod
    def detect_runtime_refs(self, content, file_path):
        """Return list of RuntimeRef dicts.

        Each dict: {target, type, line_number, statement}
        type is one of: "file_read", "http_client", "http_server", "env_var", "config_load"
        """

    @abc.abstractmethod
    def compute_metrics(self, content, file_path):
        """Return FileMetrics dict.

        Keys: loc, function_count, class_count, cyclomatic_complexity, export_count
        """
