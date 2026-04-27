"""JSON output formatting and file writing."""

import json
import os
from datetime import datetime, timezone


def build_modules(files, module_health):
    """Group files by module and attach health metrics."""
    modules = {}
    for f in files:
        mod = f['module']
        if mod not in modules:
            modules[mod] = {
                'name': mod,
                'path': (mod + '/') if mod != '(root)' else '',
                'files': [],
                'total_loc': 0,
                'file_count': 0,
            }
        modules[mod]['files'].append(f['name'])
        modules[mod]['total_loc'] += f['loc']
        modules[mod]['file_count'] += 1

    for name, data in modules.items():
        data['health'] = module_health.get(name, {
            'cohesion': 0.0, 'coupling': 0,
            'avg_complexity': 0.0, 'hottest_file': None,
        })

    return sorted(modules.values(), key=lambda m: m['name'])


def format_output(root_path, files, edges, issues,
                  runtime_edges, env_vars, entry_points, module_health):
    """Build the complete output dict ready for JSON serialization."""
    modules = build_modules(files, module_health)
    total_loc = sum(f['loc'] for f in files)

    file_records = []
    for f in files:
        file_records.append({
            'path': f['path'],
            'name': f['name'],
            'module': f['module'],
            'extension': f['extension'],
            'loc': f['loc'],
            'size_bytes': f['size_bytes'],
            'imports': f.get('imports', []),
            'imported_by': f.get('imported_by', []),
            'imported_names': f.get('imported_names_map', {}),
            'exports': f.get('exports', []),
            'status': f.get('status', 'active'),
            'metrics': f.get('metrics', {}),
            'git': f.get('git'),
        })

    return {
        'metadata': {
            'scanned_path': os.path.abspath(root_path),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_files': len(files),
            'total_loc': total_loc,
            'total_modules': len(modules),
        },
        'modules': modules,
        'files': file_records,
        'edges': edges,
        'runtime_edges': runtime_edges,
        'env_vars': env_vars,
        'entry_points': entry_points,
        'issues': issues,
    }


def write_output(data, output_path, pretty=True):
    """Write the output dict as JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)
        f.write('\n')
