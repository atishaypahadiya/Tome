// Fallback sample data if no JSON is loaded
export const FALLBACK_DATA = {
  metadata: {
    scanned_path: "/example/project",
    timestamp: new Date().toISOString(),
    total_files: 0,
    total_loc: 0,
    total_modules: 0,
  },
  modules: [],
  files: [],
  edges: [],
  runtime_edges: [],
  env_vars: [],
  entry_points: [],
  issues: {
    orphans: [],
    dead_imports: [],
    circular: [],
  },
};

export function validateScanData(data) {
  if (!data || typeof data !== 'object') return false;
  if (!data.metadata) return false;
  if (!Array.isArray(data.modules)) return false;
  if (!Array.isArray(data.files)) return false;
  if (!Array.isArray(data.edges)) return false;
  return true;
}
