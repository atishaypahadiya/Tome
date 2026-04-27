import { getModuleColor } from './colors';

const EDGE_WEIGHTS = { strong: 1.0, lazy: 0.5, conditional: 0.3, type_only: 0.1 };

function computeRadius(loc) {
  return Math.max(3, Math.min(12, Math.sqrt(loc) * 0.3));
}

export function computeLayout(scanData) {
  if (!scanData) return { nodes: [], edges: [], modules: [] };

  const { modules, files, edges } = scanData;

  // Build file-level nodes
  const nodes = files.map(file => {
    const color = getModuleColor(file.module);
    return {
      id: file.path,
      name: file.name,
      path: file.path,
      module: file.module,
      loc: file.loc || 1,
      radius: computeRadius(file.loc || 1),
      color: color.border,
      status: file.status,
    };
  });

  // Build file-level edges (only those where both source and target exist)
  const nodeIds = new Set(nodes.map(n => n.id));
  const edgeList = [];
  for (const edge of edges) {
    if (nodeIds.has(edge.from) && nodeIds.has(edge.to)) {
      edgeList.push({
        source: edge.from,
        target: edge.to,
        type: edge.type,
        weight: EDGE_WEIGHTS[edge.type] || 0.3,
      });
    }
  }

  // Build module summary for legend/clustering
  const moduleSummary = modules.map(mod => {
    const color = getModuleColor(mod.name);
    return {
      name: mod.name,
      fileCount: mod.file_count,
      totalLoc: mod.total_loc,
      color: color.border,
    };
  });

  return {
    nodes,
    edges: edgeList,
    modules: moduleSummary,
  };
}
