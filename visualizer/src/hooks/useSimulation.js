import { useState, useCallback, useMemo } from 'react';
import { findPath, findAllDownstream, getPathEdges, getDownstreamEdges } from '../utils/simulation';

export function useSimulation(moduleEdges) {
  const [simulationPath, setSimulationPath] = useState(null);
  const [simulationEdges, setSimulationEdges] = useState(null);

  const startSimulation = useCallback((source, target) => {
    if (!source) {
      setSimulationPath(null);
      setSimulationEdges(null);
      return;
    }

    if (target) {
      // Source to target path
      const path = findPath(source, target, moduleEdges);
      if (path) {
        setSimulationPath(path);
        setSimulationEdges(getPathEdges(path, moduleEdges));
      } else {
        setSimulationPath(null);
        setSimulationEdges(null);
      }
    } else {
      // All downstream from source
      const downstream = findAllDownstream(source, moduleEdges);
      setSimulationPath(downstream);
      setSimulationEdges(getDownstreamEdges(downstream, moduleEdges));
    }
  }, [moduleEdges]);

  const clearSimulation = useCallback(() => {
    setSimulationPath(null);
    setSimulationEdges(null);
  }, []);

  return {
    simulationPath,
    simulationEdges,
    startSimulation,
    clearSimulation,
  };
}
