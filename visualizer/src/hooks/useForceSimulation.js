import { useRef, useEffect, useCallback } from 'react';
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from 'd3-force';

export function useForceSimulation(nodes, edges) {
  const simulationRef = useRef(null);
  const onTickRef = useRef(null);

  const setTickCallback = useCallback((fn) => {
    onTickRef.current = fn;
  }, []);

  useEffect(() => {
    if (!nodes.length) return;

    // Arrange modules in a circle for initial positions
    const moduleNames = [...new Set(nodes.map(n => n.module))];
    const angleStep = (2 * Math.PI) / Math.max(moduleNames.length, 1);
    const clusterRadius = Math.min(600, moduleNames.length * 18);
    const moduleCentroids = new Map();

    moduleNames.forEach((mod, i) => {
      const angle = i * angleStep;
      moduleCentroids.set(mod, {
        x: Math.cos(angle) * clusterRadius,
        y: Math.sin(angle) * clusterRadius,
      });
    });

    // Set initial positions near module centroid with jitter
    for (const node of nodes) {
      const centroid = moduleCentroids.get(node.module);
      if (centroid && node.x == null) {
        node.x = centroid.x + (Math.random() - 0.5) * 120;
        node.y = centroid.y + (Math.random() - 0.5) * 120;
      }
    }

    // Custom clustering force: attract files toward their module's mean position
    function forceCluster(alpha) {
      const moduleNodes = new Map();
      for (const node of nodes) {
        if (!moduleNodes.has(node.module)) moduleNodes.set(node.module, []);
        moduleNodes.get(node.module).push(node);
      }
      for (const [, mNodes] of moduleNodes) {
        const cx = mNodes.reduce((s, n) => s + n.x, 0) / mNodes.length;
        const cy = mNodes.reduce((s, n) => s + n.y, 0) / mNodes.length;
        for (const node of mNodes) {
          node.vx += (cx - node.x) * alpha * 0.15;
          node.vy += (cy - node.y) * alpha * 0.15;
        }
      }
    }

    const sim = forceSimulation(nodes)
      .force('link', forceLink(edges)
        .id(d => d.id)
        .distance(d => 30 / (d.weight || 0.3))
        .strength(d => 0.3 * (d.weight || 0.3))
      )
      .force('charge', forceManyBody()
        .strength(-40)
        .distanceMax(300)
      )
      .force('center', forceCenter(0, 0).strength(0.05))
      .force('collide', forceCollide()
        .radius(d => d.radius + 1.5)
        .strength(0.7)
      )
      .force('cluster', forceCluster)
      .alphaDecay(0.02)
      .velocityDecay(0.3)
      .on('tick', () => {
        onTickRef.current?.();
      });

    simulationRef.current = sim;

    return () => {
      sim.stop();
      simulationRef.current = null;
    };
  }, [nodes, edges]);

  const reheat = useCallback(() => {
    simulationRef.current?.alpha(0.3).restart();
  }, []);

  return {
    simulationRef,
    setTickCallback,
    reheat,
  };
}
