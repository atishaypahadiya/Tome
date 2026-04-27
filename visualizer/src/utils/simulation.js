/**
 * Find shortest path between two modules using BFS
 */
export function findPath(sourceModule, targetModule, moduleEdges) {
  const adjacency = new Map();
  for (const edge of moduleEdges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    adjacency.get(edge.source).push(edge.target);
  }

  const visited = new Set();
  const queue = [[sourceModule]];
  visited.add(sourceModule);

  while (queue.length > 0) {
    const path = queue.shift();
    const current = path[path.length - 1];

    if (current === targetModule) return path;

    const neighbors = adjacency.get(current) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([...path, neighbor]);
      }
    }
  }

  return null; // No path found
}

/**
 * Find all downstream dependencies from a module using DFS
 */
export function findAllDownstream(sourceModule, moduleEdges) {
  const adjacency = new Map();
  for (const edge of moduleEdges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    adjacency.get(edge.source).push(edge.target);
  }

  const visited = new Set();
  const result = [sourceModule];

  function dfs(current) {
    visited.add(current);
    const neighbors = adjacency.get(current) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        result.push(neighbor);
        dfs(neighbor);
      }
    }
  }

  dfs(sourceModule);
  return result;
}

/**
 * Get all edges that are part of the given path
 */
export function getPathEdges(path, moduleEdges) {
  if (!path || path.length < 2) return new Set();

  const pathEdgeKeys = new Set();
  for (let i = 0; i < path.length - 1; i++) {
    pathEdgeKeys.add(`${path[i]}|${path[i + 1]}`);
  }

  return pathEdgeKeys;
}

/**
 * Get all edges connected to any module in the path
 */
export function getDownstreamEdges(modules, moduleEdges) {
  const moduleSet = new Set(modules);
  const edgeKeys = new Set();

  for (const edge of moduleEdges) {
    if (moduleSet.has(edge.source) && moduleSet.has(edge.target)) {
      edgeKeys.add(`${edge.source}|${edge.target}`);
    }
  }

  return edgeKeys;
}
