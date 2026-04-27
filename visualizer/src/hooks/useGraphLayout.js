import { useMemo } from 'react';
import { computeLayout } from '../utils/layout';

export function useGraphLayout(scanData) {
  return useMemo(() => {
    if (!scanData) return { nodes: [], edges: [], modules: [] };
    return computeLayout(scanData);
  }, [scanData]);
}
