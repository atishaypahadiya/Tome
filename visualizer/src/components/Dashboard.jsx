import { memo, useState } from 'react';
import { getModuleColor } from '../utils/colors';

function Dashboard({ scanData, onSelectModule }) {
  const { metadata, modules, files, edges, issues, env_vars } = scanData;
  const [sortKey, setSortKey] = useState('total_loc');
  const [sortDir, setSortDir] = useState(-1);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => -d);
    } else {
      setSortKey(key);
      setSortDir(-1);
    }
  };

  const sortedModules = [...modules].sort((a, b) => {
    let av, bv;
    switch (sortKey) {
      case 'name': av = a.name; bv = b.name; return sortDir * av.localeCompare(bv);
      case 'file_count': av = a.file_count; bv = b.file_count; break;
      case 'total_loc': av = a.total_loc; bv = b.total_loc; break;
      case 'cohesion': av = a.health?.cohesion || 0; bv = b.health?.cohesion || 0; break;
      case 'coupling': av = a.health?.coupling || 0; bv = b.health?.coupling || 0; break;
      case 'complexity': av = a.health?.avg_complexity || 0; bv = b.health?.avg_complexity || 0; break;
      default: av = a.total_loc; bv = b.total_loc;
    }
    return sortDir * (av - bv);
  });

  // Top files
  const topByLOC = [...files].sort((a, b) => b.loc - a.loc).slice(0, 10);
  const topByComplexity = [...files].sort((a, b) => (b.metrics?.cyclomatic_complexity || 0) - (a.metrics?.cyclomatic_complexity || 0)).slice(0, 10);
  const topByChanges = [...files].filter(f => f.git?.change_count > 0).sort((a, b) => (b.git?.change_count || 0) - (a.git?.change_count || 0)).slice(0, 10);
  const topByHotspot = [...files].filter(f => f.git?.hotspot_score > 0).sort((a, b) => (b.git?.hotspot_score || 0) - (a.git?.hotspot_score || 0)).slice(0, 10);

  const edgeTypes = {};
  for (const e of edges) {
    edgeTypes[e.type] = (edgeTypes[e.type] || 0) + 1;
  }

  return (
    <div style={{
      width: '100%',
      height: '100%',
      overflow: 'auto',
      background: 'var(--bg-primary)',
      padding: 24,
      fontFamily: 'var(--font-mono)',
    }}>
      {/* Row 1: Summary Cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <SummaryCard label="Total Files" value={metadata.total_files} />
        <SummaryCard label="Total LOC" value={formatLOC(metadata.total_loc)} />
        <SummaryCard label="Modules" value={metadata.total_modules} />
        <SummaryCard label="Edges" value={edges.length} />
        <SummaryCard label="Strong" value={edgeTypes.strong || 0} color="var(--text-secondary)" />
        <SummaryCard label="Lazy" value={edgeTypes.lazy || 0} color="var(--status-warn)" />
        <SummaryCard label="Conditional" value={edgeTypes.conditional || 0} color="var(--text-dim)" />
      </div>

      {/* Row 2: Module Health Table */}
      <SectionLabel>Module Health</SectionLabel>
      <div style={{ overflowX: 'auto', marginBottom: 24 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
          <thead>
            <tr>
              {[
                { key: 'name', label: 'Module' },
                { key: 'file_count', label: 'Files' },
                { key: 'total_loc', label: 'LOC' },
                { key: 'cohesion', label: 'Cohesion' },
                { key: 'coupling', label: 'Coupling' },
                { key: 'complexity', label: 'Avg Complexity' },
              ].map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  style={{
                    textAlign: col.key === 'name' ? 'left' : 'right',
                    padding: '8px 10px',
                    color: sortKey === col.key ? 'var(--text-primary)' : 'var(--text-dim)',
                    cursor: 'pointer',
                    borderBottom: '1px solid var(--border)',
                    fontWeight: 500,
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                  }}
                >
                  {col.label} {sortKey === col.key ? (sortDir > 0 ? '↑' : '↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedModules.map((mod, i) => {
              const color = getModuleColor(mod.name);
              const h = mod.health || {};
              return (
                <tr
                  key={mod.name}
                  onClick={() => onSelectModule(mod.name)}
                  style={{
                    cursor: 'pointer',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(14, 20, 32, 0.3)',
                    transition: 'background 150ms',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(14, 20, 32, 0.5)'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(14, 20, 32, 0.3)'}
                >
                  <td style={{ padding: '6px 10px', color: color.text }}>{mod.name}</td>
                  <td style={tdRight}>{mod.file_count}</td>
                  <td style={tdRight}>{formatLOC(mod.total_loc)}</td>
                  <td style={{ ...tdRight, color: cellColor(h.cohesion, [0.5, 0.2]) }}>
                    {((h.cohesion || 0) * 100).toFixed(0)}%
                  </td>
                  <td style={{ ...tdRight, color: cellColor(h.coupling, [5, 10], true) }}>
                    {h.coupling || 0}
                  </td>
                  <td style={{ ...tdRight, color: cellColor(h.avg_complexity, [20, 50], true) }}>
                    {(h.avg_complexity || 0).toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Row 3: Issues */}
      <SectionLabel>Issues</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 24 }}>
        <IssuePanel
          title={`Dead Imports (${issues?.dead_imports?.length || 0})`}
          items={(issues?.dead_imports || []).map(d => ({
            primary: d.file,
            secondary: d.symbol || d.imports,
            detail: d.reason,
          }))}
          color="var(--status-error)"
        />
        <IssuePanel
          title={`Orphans (${issues?.orphans?.length || 0})`}
          items={(issues?.orphans || []).map(o => ({ primary: o }))}
          color="var(--status-warn)"
        />
        <IssuePanel
          title={`Circular Deps (${issues?.circular?.length || 0})`}
          items={(issues?.circular || []).map(c => ({
            primary: c.cycle.map(p => p.split('/').pop()).join(' → '),
            detail: c.severity,
          }))}
          color="var(--status-warn)"
        />
      </div>

      {/* Row 4: Env Vars */}
      {env_vars && env_vars.length > 0 && (
        <>
          <SectionLabel>Environment Variables ({env_vars.length})</SectionLabel>
          <div style={{ overflowX: 'auto', marginBottom: 24 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
              <thead>
                <tr>
                  <th style={{ ...thStyle, textAlign: 'left' }}>Variable</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>References</th>
                </tr>
              </thead>
              <tbody>
                {[...env_vars].sort((a, b) => b.referenced_by.length - a.referenced_by.length).map(ev => (
                  <tr key={ev.name}>
                    <td style={{ padding: '4px 10px', color: 'var(--status-warn)' }}>{ev.name}</td>
                    <td style={tdRight}>{ev.referenced_by.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Row 5: Top Files */}
      <SectionLabel>Top Files</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
        <TopFilesList title="By LOC" files={topByLOC} metricKey="loc" />
        <TopFilesList title="By Complexity" files={topByComplexity} metricKey="complexity" />
        <TopFilesList title="By Git Changes" files={topByChanges} metricKey="changes" />
        <TopFilesList title="By Hotspot Score" files={topByHotspot} metricKey="hotspot" />
      </div>
    </div>
  );
}

const tdRight = { padding: '6px 10px', textAlign: 'right', color: 'var(--text-secondary)' };

const thStyle = {
  padding: '8px 10px',
  color: 'var(--text-dim)',
  borderBottom: '1px solid var(--border)',
  fontWeight: 500,
};

function SummaryCard({ label, value, color }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '16px 20px',
      minWidth: 120,
    }}>
      <div style={{ fontSize: 24, fontWeight: 700, color: color || 'var(--text-primary)' }}>{value}</div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>{label}</div>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 10,
      fontWeight: 600,
      color: 'var(--text-dim)',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      marginBottom: 12,
    }}>
      {children}
    </div>
  );
}

function IssuePanel({ title, items, color }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 12,
      maxHeight: 200,
      overflowY: 'auto',
    }}>
      <div style={{ fontSize: 10, fontWeight: 600, color, marginBottom: 8 }}>{title}</div>
      {items.length === 0 ? (
        <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>None</div>
      ) : (
        items.map((item, i) => (
          <div key={i} style={{ fontSize: 9, color: 'var(--text-secondary)', padding: '2px 0' }}>
            <div>{item.primary}</div>
            {item.secondary && <div style={{ color: 'var(--text-dim)' }}>{item.secondary}</div>}
            {item.detail && <div style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>{item.detail}</div>}
          </div>
        ))
      )}
    </div>
  );
}

function TopFilesList({ title, files, metricKey }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 12,
    }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>{title}</div>
      {files.map((f, i) => {
        let value;
        switch (metricKey) {
          case 'loc': value = f.loc; break;
          case 'complexity': value = f.metrics?.cyclomatic_complexity || 0; break;
          case 'changes': value = f.git?.change_count || 0; break;
          case 'hotspot': value = f.git?.hotspot_score || 0; break;
          default: value = 0;
        }
        return (
          <div key={f.path} style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 9,
            padding: '2px 0',
          }}>
            <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, marginRight: 8 }}>
              {i + 1}. {f.path}
            </span>
            <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>{value}</span>
          </div>
        );
      })}
    </div>
  );
}

function cellColor(value, thresholds, inverse = false) {
  if (value == null) return 'var(--text-dim)';
  if (inverse) {
    // Higher is worse
    if (value > thresholds[1]) return 'var(--status-error)';
    if (value > thresholds[0]) return 'var(--status-warn)';
    return 'var(--status-ok)';
  } else {
    // Higher is better
    if (value > thresholds[0]) return 'var(--status-ok)';
    if (value > thresholds[1]) return 'var(--status-warn)';
    return 'var(--status-error)';
  }
}

function formatLOC(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

export default memo(Dashboard);
