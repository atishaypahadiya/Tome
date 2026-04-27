"""Analysis: smart classification, dead imports, circular deps, runtime edges, module health."""

from tome.config import FILE_CATEGORIES, BUILD_FILENAMES, PYTHON_EXTENSIONS, JS_TS_EXTENSIONS


# ---------- reverse deps + classification ------------------------------------

def build_imported_by(files):
    """Populate each file's 'imported_by' list (reverse graph)."""
    reverse = {f['path']: [] for f in files}
    for f in files:
        for t in f.get('imports', []):
            if t in reverse:
                reverse[t].append(f['path'])
    for f in files:
        f['imported_by'] = sorted(reverse.get(f['path'], []))


def classify_files(files):
    """Assign a status to every file using smart categories."""
    for f in files:
        has_imp = bool(f.get('imports'))
        is_imp = bool(f.get('imported_by'))
        is_entry = f.get('is_entry_point', False)
        ext = f['extension']
        name = f['name']
        loc = f['loc']
        metrics = f.get('metrics', {})

        if has_imp or is_imp:
            f['status'] = 'entry_point' if (is_entry and not is_imp) else 'active'
            continue
        if is_entry:
            f['status'] = 'entry_point'
            continue
        if name in BUILD_FILENAMES:
            f['status'] = 'build'
            continue
        cat = FILE_CATEGORIES.get(ext)
        if cat:
            f['status'] = cat
            continue
        if name == '__init__.py' and loc < 10 and metrics.get('function_count', 0) == 0 and metrics.get('class_count', 0) == 0:
            f['status'] = 'namespace'
            continue
        if ext == '.json':
            lp = f['path'].lower()
            f['status'] = 'data' if any(s in lp for s in ('data', 'fixtures', 'skills/apps', 'seed', 'mock')) else 'config'
            continue
        if ext in PYTHON_EXTENSIONS | JS_TS_EXTENSIONS:
            f['status'] = 'code_orphan'
            continue
        f['status'] = 'config' if not ext else 'code_orphan'


# ---------- symbol-level dead imports ----------------------------------------

def check_symbol_imports(files, edges):
    """Flag imports of symbols not in the target file's export list."""
    export_map = {}
    for f in files:
        export_map[f['path']] = {e['name'] for e in f.get('exports', [])}

    out = []
    for edge in edges:
        names = edge.get('imported_names', [])
        if not names or '*' in names:
            continue
        stmt = edge.get('import_statement', '')
        if stmt.startswith('import ') and ' from ' not in stmt.lower():
            continue
        exports = export_map.get(edge['to'])
        if exports is None or not exports:
            continue
        for n in names:
            if n not in exports:
                out.append({
                    'file': edge['from'],
                    'imports': stmt,
                    'symbol': n,
                    'reason': f"symbol '{n}' not found in target file",
                })
    return out


# ---------- circular deps with severity --------------------------------------

def find_circular_deps(files):
    graph = {f['path']: f.get('imports', []) for f in files}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    cycles = []
    seen = set()

    for start in graph:
        if color[start] != WHITE:
            continue
        stack, path = [(start, 0)], []
        while stack:
            node, ci = stack.pop()
            if ci == 0:
                color[node] = GRAY
                path.append(node)
            else:
                while path and path[-1] != node:
                    path.pop()
            nbrs = graph.get(node, [])
            nxt = None
            for i in range(ci, len(nbrs)):
                nb = nbrs[i]
                if nb not in color:
                    continue
                if color[nb] == GRAY:
                    try:
                        idx = path.index(nb)
                    except ValueError:
                        continue
                    cycle = path[idx:] + [nb]
                    body = cycle[:-1]
                    mi = body.index(min(body))
                    key = tuple(body[mi:] + body[:mi])
                    if key not in seen:
                        seen.add(key)
                        cycles.append({'cycle': cycle, 'severity': _cycle_severity(cycle)})
                elif color[nb] == WHITE:
                    nxt = (i, nb)
                    break
            if nxt:
                stack.append((node, nxt[0] + 1))
                stack.append((nxt[1], 0))
            else:
                color[node] = BLACK
                if path and path[-1] == node:
                    path.pop()
    return cycles


def _cycle_severity(cycle):
    paths = cycle[:-1]
    if len(paths) == 2:
        a, b = paths
        da, db = '/'.join(a.split('/')[:-1]), '/'.join(b.split('/')[:-1])
        na, nb = a.split('/')[-1], b.split('/')[-1]
        if da == db and (na == '__init__.py' or nb == '__init__.py'):
            return 'structural'
        if na == '__init__.py' and b.startswith(da + '/'):
            return 'structural'
        if nb == '__init__.py' and a.startswith(db + '/'):
            return 'structural'
    tops = set()
    for p in paths:
        parts = p.split('/')
        tops.add(parts[0] if len(parts) > 1 else '(root)')
    return 'runtime' if len(tops) > 1 else 'structural'


# ---------- runtime / cross-language edges -----------------------------------

def build_runtime_edges(files, all_paths):
    """Match HTTP server routes to client fetches, collect env vars, etc.

    Returns (runtime_edges_list, env_vars_list).
    """
    server_routes = {}   # path_str -> file
    client_urls = {}     # path_str -> file
    env_vars = {}        # var_name -> set(files)
    data_edges = []
    config_edges = []

    for f in files:
        fp = f['path']
        for ref in f.get('runtime_refs', []):
            rt = ref.get('type')
            tgt = ref.get('target', '')
            if rt == 'http_server':
                server_routes[tgt] = fp
            elif rt == 'http_client':
                url = tgt
                if url.startswith('http'):
                    parts = url.split('/', 3)
                    url = ('/' + parts[3]) if len(parts) >= 4 else url
                client_urls[url] = fp
            elif rt == 'env_var':
                env_vars.setdefault(tgt, set()).add(fp)
            elif rt == 'file_read' and tgt in all_paths:
                data_edges.append({
                    'from': fp, 'to': tgt, 'type': 'data',
                    'import_statement': ref.get('statement', ''),
                    'imported_names': [], 'line_number': ref.get('line_number', 0),
                    'context': 'top_level',
                })
            elif rt == 'config_load' and tgt in all_paths:
                config_edges.append({
                    'from': fp, 'to': tgt, 'type': 'config',
                    'import_statement': ref.get('statement', ''),
                    'imported_names': [], 'line_number': ref.get('line_number', 0),
                    'context': 'top_level',
                })

    http_edges = []
    for curl, cfile in client_urls.items():
        for sroute, sfile in server_routes.items():
            if curl == sroute or curl.startswith(sroute) or sroute.startswith(curl):
                http_edges.append({
                    'from': cfile, 'to': sfile, 'type': 'http',
                    'client_url': curl, 'server_route': sroute,
                })

    env_list = [{'name': n, 'referenced_by': sorted(fs)} for n, fs in sorted(env_vars.items())]
    return http_edges + data_edges + config_edges, env_list


# ---------- module health ----------------------------------------------------

def compute_module_health(files, edges):
    """Return dict  module_name -> {cohesion, coupling, avg_complexity, hottest_file}."""
    mod_files = {}
    for f in files:
        mod_files.setdefault(f['module'], []).append(f)
    file_mod = {f['path']: f['module'] for f in files}

    health = {}
    for mod, mf in mod_files.items():
        paths = {f['path'] for f in mf}
        n = len(mf)

        internal = sum(1 for e in edges if e['from'] in paths and e['to'] in paths)
        possible = n * (n - 1) if n > 1 else 1
        cohesion = round(internal / possible, 2)

        ext_mods = set()
        for f in mf:
            for imp in f.get('imports', []):
                m2 = file_mod.get(imp)
                if m2 and m2 != mod:
                    ext_mods.add(m2)
            for imp in f.get('imported_by', []):
                m2 = file_mod.get(imp)
                if m2 and m2 != mod:
                    ext_mods.add(m2)

        ccs = [f.get('metrics', {}).get('cyclomatic_complexity', 0) for f in mf]
        hottest, hot_cc = None, 0
        for f in mf:
            cc = f.get('metrics', {}).get('cyclomatic_complexity', 0)
            if cc > hot_cc:
                hot_cc, hottest = cc, f['name']

        health[mod] = {
            'cohesion': cohesion,
            'coupling': len(ext_mods),
            'avg_complexity': round(sum(ccs) / len(ccs), 1) if ccs else 0.0,
            'hottest_file': hottest,
        }
    return health


# ---------- main entry point -------------------------------------------------

def analyze(files, dead_imports, edges, verbose=False):
    """Run every analysis pass.

    Returns (issues, runtime_edges, env_vars, entry_points, module_health).
    """
    all_paths = {f['path'] for f in files}

    build_imported_by(files)
    classify_files(files)

    # Recalculate hotspot scores now that imported_by is populated
    for f in files:
        git = f.get('git')
        if git:
            git['hotspot_score'] = git.get('change_count', 0) * len(f.get('imported_by', []))

    orphans = [f['path'] for f in files if f.get('status') == 'code_orphan']
    circular = find_circular_deps(files)
    sym_dead = check_symbol_imports(files, edges)

    all_dead = [{'file': d['file'], 'imports': d['imports'], 'reason': d['reason']}
                for d in dead_imports]
    for d in sym_dead:
        all_dead.append({'file': d['file'], 'imports': d['imports'],
                         'symbol': d.get('symbol', ''), 'reason': d['reason']})

    runtime_edges, env_vars = build_runtime_edges(files, all_paths)
    entry_points = sorted({f['path'] for f in files
                           if f.get('status') == 'entry_point' or f.get('is_entry_point')})
    module_health = compute_module_health(files, edges)

    if verbose:
        print(f"\n  Analysis complete:")
        print(f"    Code orphans: {len(orphans)}")
        print(f"    Dead imports: {len(all_dead)}")
        print(f"    Circular deps: {len(circular)}")
        print(f"    Runtime edges: {len(runtime_edges)}")
        print(f"    Env vars tracked: {len(env_vars)}")
        print(f"    Entry points: {len(entry_points)}")

    issues = {'orphans': orphans, 'dead_imports': all_dead, 'circular': circular}
    return issues, runtime_edges, env_vars, entry_points, module_health
