"""Parser registry and import resolution."""

import os

from tome.scanner.parsers.python_parser import PythonParser
from tome.scanner.parsers.js_parser import JSParser

_PARSERS = {
    '.py': PythonParser(),
    '.js': JSParser(),
    '.jsx': JSParser(),
    '.ts': JSParser(),
    '.tsx': JSParser(),
}

_JS_RESOLVE_EXTS = ['.ts', '.tsx', '.js', '.jsx']
_JS_INDEX_FILES = ['index.ts', 'index.tsx', 'index.js', 'index.jsx']

_CONTEXT_TO_EDGE = {
    'top_level': 'strong',
    'lazy': 'lazy',
    'conditional': 'conditional',
    'type_only': 'type_only',
}


def get_parser_for_extension(ext):
    """Return parser instance for *ext*, or None."""
    return _PARSERS.get(ext)


# ---------- resolution helpers ------------------------------------------------

def _norm(p):
    return os.path.normpath(p).replace(os.sep, '/')


def _resolve_py(imp, file_path, all_paths, top_dirs):
    raw = imp.get('_raw', {})
    module = raw.get('module') or ''
    level = raw.get('level', 0)
    names = raw.get('names') or []

    cands = []
    if level > 0:
        cur = os.path.dirname(file_path)
        for _ in range(level - 1):
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        if module:
            base = '/'.join([cur] + module.split('.')) if cur else '/'.join(module.split('.'))
            cands += [base + '.py', base + '/__init__.py']
        if names:
            nb = '/'.join([cur] + module.split('.')) if module else cur
            for n in names:
                if n == '*':
                    continue
                cands += [f'{nb}/{n}.py', f'{nb}/{n}/__init__.py'] if nb else [f'{n}.py', f'{n}/__init__.py']
    else:
        first = module.split('.')[0] if module else ''
        if first not in top_dirs:
            return []
        parts = module.split('.')
        base = '/'.join(parts)
        cands += [base + '.py', base + '/__init__.py']
        if names:
            for n in names:
                if n == '*':
                    continue
                cands += ['/'.join(parts + [n]) + '.py', '/'.join(parts + [n]) + '/__init__.py']

    seen, out = set(), []
    for c in cands:
        c = _norm(c)
        if c not in seen and c in all_paths:
            seen.add(c)
            out.append(c)
    return out


def _resolve_js(imp, file_path, all_paths):
    raw_path = (imp.get('_raw') or {}).get('raw_path', '')
    if not raw_path.startswith('.'):
        return None
    target = _norm(os.path.join(os.path.dirname(file_path), raw_path))
    if target in all_paths:
        return target
    for ext in _JS_RESOLVE_EXTS:
        if target + ext in all_paths:
            return target + ext
    for idx in _JS_INDEX_FILES:
        if target + '/' + idx in all_paths:
            return target + '/' + idx
    return None


# ---------- public API --------------------------------------------------------

def resolve_all_imports(files, verbose=False):
    """Resolve raw imports to codebase paths.  Mutates *files*.

    Returns (edges, dead_imports).
    """
    all_paths = {f['path'] for f in files}
    top_dirs = set()
    for f in files:
        parts = f['path'].split('/')
        if len(parts) > 1:
            top_dirs.add(parts[0])
        if parts[0].endswith('.py'):
            top_dirs.add(parts[0][:-3])

    edges = []
    dead_imports = []

    for f in files:
        ext = f['extension']
        fpath = f['path']
        resolved = {}          # target_path -> info dict
        names_map = {}         # target_path -> [names]

        for imp in f.get('raw_imports', []):
            raw = imp.get('_raw', {})
            stmt = imp.get('import_statement', '')
            ctx = imp.get('context', 'top_level')
            names = imp.get('imported_names', [])
            lineno = imp.get('line_number', 0)

            if ext == '.py':
                rpaths = _resolve_py(imp, fpath, all_paths, top_dirs)
                if rpaths:
                    for rp in rpaths:
                        if rp != fpath:
                            resolved[rp] = dict(stmt=stmt, ctx=ctx, names=names, lineno=lineno)
                            names_map[rp] = names
                else:
                    lv = raw.get('level', 0)
                    mod = raw.get('module') or ''
                    if lv > 0:
                        dead_imports.append({'file': fpath, 'imports': mod or '(relative)',
                                             'reason': 'target not found', 'statement': stmt})
                    elif mod and mod.split('.')[0] in top_dirs:
                        dead_imports.append({'file': fpath, 'imports': mod,
                                             'reason': 'target not found', 'statement': stmt})

            elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
                rp = _resolve_js(imp, fpath, all_paths)
                if rp and rp != fpath:
                    resolved[rp] = dict(stmt=stmt, ctx=ctx, names=names, lineno=lineno)
                    names_map[rp] = names
                elif raw.get('raw_path', '').startswith('.'):
                    dead_imports.append({'file': fpath, 'imports': raw.get('raw_path', ''),
                                         'reason': 'target not found', 'statement': stmt})

        f['imports'] = sorted(resolved)
        f['import_statements'] = {k: v['stmt'] for k, v in resolved.items()}
        f['imported_names_map'] = names_map

        for target, info in resolved.items():
            edges.append({
                'from': fpath,
                'to': target,
                'type': _CONTEXT_TO_EDGE.get(info['ctx'], 'strong'),
                'import_statement': info['stmt'],
                'imported_names': info['names'],
                'line_number': info['lineno'],
                'context': info['ctx'],
            })

        if verbose and resolved:
            print(f"  [imports] {fpath} -> {len(resolved)} resolved")

    return edges, dead_imports
