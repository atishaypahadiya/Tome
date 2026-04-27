import { useRef, useEffect, useCallback, useState, memo } from 'react';
import { zoom, zoomIdentity } from 'd3-zoom';
import { select } from 'd3-selection';
import { drag } from 'd3-drag';

function GraphView({
  nodes,
  edges,
  scanData,
  selectedFile,
  hoveredFile,
  simulationRef,
  setTickCallback,
  simulationPath,
  onSelectFile,
  onHoverFile,
  onBackgroundClick,
}) {
  const svgRef = useRef(null);
  const zoomGroupRef = useRef(null);
  const edgesGroupRef = useRef(null);
  const nodesGroupRef = useRef(null);
  const labelsGroupRef = useRef(null);
  const zoomRef = useRef(null);
  const [tooltipData, setTooltipData] = useState(null);

  // d3-zoom setup
  useEffect(() => {
    const svg = select(svgRef.current);

    const zoomBehavior = zoom()
      .scaleExtent([0.1, 8.0])
      .on('zoom', (event) => {
        select(zoomGroupRef.current).attr('transform', event.transform);
        // Progressive label visibility based on zoom + node size
        const k = event.transform.k;
        select(labelsGroupRef.current).selectAll('text')
          .style('display', d => {
            if (k > 4.0) return null;                   // show all at very high zoom
            if (k > 2.8 && d.radius >= 6) return null;  // large nodes at high zoom
            if (k > 2.0 && d.radius >= 9) return null;  // biggest nodes at moderate zoom
            return 'none';
          })
          .style('opacity', d => {
            if (k > 4.0) return 0.7;
            if (k > 2.8 && d.radius >= 6) return 0.6;
            if (k > 2.0 && d.radius >= 9) return 0.5;
            return 0;
          });
      });

    svg.call(zoomBehavior);
    svg.on('dblclick.zoom', null);
    zoomRef.current = zoomBehavior;

    return () => svg.on('.zoom', null);
  }, []);

  // Create and update d3 elements
  useEffect(() => {
    if (!nodes.length) return;

    const edgesGroup = select(edgesGroupRef.current);
    const nodesGroup = select(nodesGroupRef.current);
    const labelsGroup = select(labelsGroupRef.current);

    // EDGES: data join
    const lines = edgesGroup.selectAll('line').data(edges, d => {
      const sid = d.source.id || d.source;
      const tid = d.target.id || d.target;
      return `${sid}-${tid}`;
    });
    lines.exit().remove();
    const linesEnter = lines.enter().append('line')
      .attr('stroke', 'rgba(180, 200, 220, 0.07)')
      .attr('stroke-width', 0.4)
      .attr('stroke-opacity', 1);
    linesEnter.merge(lines);

    // NODES: data join
    const circles = nodesGroup.selectAll('circle').data(nodes, d => d.id);
    circles.exit().remove();
    const circlesEnter = circles.enter().append('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => d.color)
      .attr('stroke', 'none')
      .attr('cursor', 'pointer')
      .attr('filter', 'url(#node-glow)')
      .on('click', (event, d) => {
        event.stopPropagation();
        onSelectFile(d.id);
      })
      .on('mouseenter', (event, d) => {
        select(event.currentTarget)
          .attr('stroke', 'rgba(255,255,255,0.6)')
          .attr('stroke-width', 1.5)
          .attr('filter', 'url(#node-glow-hover)');
        onHoverFile(d);
        setTooltipData({ x: d.x, y: d.y, name: d.name, module: d.module, loc: d.loc });
      })
      .on('mouseleave', (event) => {
        select(event.currentTarget)
          .attr('stroke', 'none')
          .attr('filter', 'url(#node-glow)');
        onHoverFile(null);
        setTooltipData(null);
      });
    circlesEnter.merge(circles);

    // DRAG behavior
    const dragBehavior = drag()
      .on('start', (event, d) => {
        if (!event.active) simulationRef.current?.alphaTarget(0.1).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulationRef.current?.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
    nodesGroup.selectAll('circle').call(dragBehavior);

    // LABELS: data join (hidden by default)
    const labels = labelsGroup.selectAll('text').data(nodes, d => d.id);
    labels.exit().remove();
    labels.enter().append('text')
      .attr('font-size', 8)
      .attr('font-family', 'var(--font-mono)')
      .attr('fill', 'rgba(200, 210, 220, 0.5)')
      .attr('text-anchor', 'middle')
      .attr('dy', d => -d.radius - 3)
      .attr('pointer-events', 'none')
      .text(d => d.name)
      .style('display', 'none');

    // TICK callback: update positions every frame
    const allLines = edgesGroup.selectAll('line');
    const allCircles = nodesGroup.selectAll('circle');
    const allLabels = labelsGroup.selectAll('text');

    setTickCallback(() => {
      allLines
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      allCircles
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);
      allLabels
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

    // Fit viewport after simulation settles a bit
    const timer = setTimeout(() => fitViewport(), 1500);
    return () => clearTimeout(timer);
  }, [nodes, edges, setTickCallback, onSelectFile, onHoverFile]);

  // Selection highlighting
  useEffect(() => {
    const nodesGroup = select(nodesGroupRef.current);
    const edgesGroup = select(edgesGroupRef.current);

    if (selectedFile) {
      const connected = new Set([selectedFile]);
      for (const e of edges) {
        const sid = e.source.id ?? e.source;
        const tid = e.target.id ?? e.target;
        if (sid === selectedFile) connected.add(tid);
        if (tid === selectedFile) connected.add(sid);
      }
      nodesGroup.selectAll('circle')
        .attr('opacity', d => connected.has(d.id) ? 1 : 0.06)
        .attr('filter', d => connected.has(d.id) ? 'url(#node-glow-hover)' : 'none');
      edgesGroup.selectAll('line')
        .attr('stroke-opacity', d => {
          const sid = d.source.id ?? d.source;
          const tid = d.target.id ?? d.target;
          return (sid === selectedFile || tid === selectedFile) ? 1 : 1;
        })
        .attr('stroke', d => {
          const sid = d.source.id ?? d.source;
          const tid = d.target.id ?? d.target;
          return (sid === selectedFile || tid === selectedFile) ? 'rgba(200, 215, 230, 0.35)' : 'rgba(180, 200, 220, 0.02)';
        });
    } else if (simulationPath) {
      const pathSet = new Set(simulationPath);
      const fileToModule = new Map();
      if (scanData) {
        for (const f of scanData.files) fileToModule.set(f.path, f.module);
      }
      nodesGroup.selectAll('circle')
        .attr('opacity', d => pathSet.has(d.module) ? 1 : 0.06)
        .attr('filter', d => pathSet.has(d.module) ? 'url(#node-glow-hover)' : 'none');
      edgesGroup.selectAll('line')
        .attr('stroke-opacity', d => {
          const sm = fileToModule.get(d.source.id ?? d.source);
          const tm = fileToModule.get(d.target.id ?? d.target);
          return pathSet.has(sm) && pathSet.has(tm) ? 1 : 1;
        })
        .attr('stroke', d => {
          const sm = fileToModule.get(d.source.id ?? d.source);
          const tm = fileToModule.get(d.target.id ?? d.target);
          return pathSet.has(sm) && pathSet.has(tm) ? 'rgba(200, 220, 240, 0.4)' : 'rgba(180, 200, 220, 0.02)';
        });
    } else {
      nodesGroup.selectAll('circle')
        .attr('opacity', 1)
        .attr('filter', 'url(#node-glow)');
      edgesGroup.selectAll('line')
        .attr('stroke-opacity', 1)
        .attr('stroke', 'rgba(180, 200, 220, 0.07)');
    }
  }, [selectedFile, simulationPath, edges, scanData]);

  // Fit viewport
  const fitViewport = useCallback(() => {
    if (!nodes.length || !svgRef.current || !zoomRef.current) return;
    const svg = svgRef.current;
    const { width, height } = svg.getBoundingClientRect();
    if (width === 0 || height === 0) return;

    const padding = 60;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x == null || n.y == null) continue;
      minX = Math.min(minX, n.x - n.radius);
      maxX = Math.max(maxX, n.x + n.radius);
      minY = Math.min(minY, n.y - n.radius);
      maxY = Math.max(maxY, n.y + n.radius);
    }
    if (minX === Infinity) return;

    const cw = maxX - minX + padding * 2;
    const ch = maxY - minY + padding * 2;
    const scale = Math.min(width / cw, height / ch, 2.0);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const tx = width / 2 - cx * scale;
    const ty = height / 2 - cy * scale;

    select(svgRef.current).call(
      zoomRef.current.transform,
      zoomIdentity.translate(tx, ty).scale(scale)
    );
  }, [nodes]);

  // Listen for fit-viewport event
  useEffect(() => {
    window.addEventListener('tome:fit-viewport', fitViewport);
    return () => window.removeEventListener('tome:fit-viewport', fitViewport);
  }, [fitViewport]);

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      style={{ display: 'block' }}
      onClick={onBackgroundClick}
    >
      {/* Deep navy gradient background */}
      <defs>
        <radialGradient id="bg-gradient" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stopColor="#0c1220" />
          <stop offset="60%" stopColor="#080c14" />
          <stop offset="100%" stopColor="#040810" />
        </radialGradient>
        {/* Subtle node glow */}
        <filter id="node-glow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
          <feColorMatrix in="blur" type="matrix"
            values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.6 0"
            result="glow" />
          <feMerge>
            <feMergeNode in="glow" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Brighter hover glow */}
        <filter id="node-glow-hover" x="-150%" y="-150%" width="400%" height="400%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
          <feColorMatrix in="blur" type="matrix"
            values="1 0 0 0 0.1  0 1 0 0 0.1  0 0 1 0 0.15  0 0 0 1.2 0"
            result="glow" />
          <feMerge>
            <feMergeNode in="glow" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="100%" height="100%" fill="url(#bg-gradient)" />
      <g ref={zoomGroupRef}>
        <g ref={edgesGroupRef} />
        <g ref={nodesGroupRef} />
        <g ref={labelsGroupRef} />
      </g>
      {/* Tooltip */}
      {tooltipData && (
        <g style={{ pointerEvents: 'none' }}>
          <foreignObject
            x={tooltipData.x + 12}
            y={tooltipData.y - 30}
            width={220}
            height={50}
            style={{ overflow: 'visible' }}
          >
            <div
              xmlns="http://www.w3.org/1999/xhtml"
              style={{
                background: 'rgba(8, 12, 20, 0.95)',
                border: '1px solid rgba(60, 80, 110, 0.3)',
                borderRadius: 6,
                padding: '4px 8px',
                fontSize: 9,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
                width: 'fit-content',
                backdropFilter: 'blur(8px)',
              }}
            >
              <div style={{ color: 'var(--text-primary)', fontSize: 10 }}>{tooltipData.name}</div>
              <div>{tooltipData.module} · {tooltipData.loc} LOC</div>
            </div>
          </foreignObject>
        </g>
      )}
    </svg>
  );
}

export default memo(GraphView);
