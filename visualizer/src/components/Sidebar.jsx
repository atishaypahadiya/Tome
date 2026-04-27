import { memo, useState } from 'react';
import { getModuleColor } from '../utils/colors';

const sectionHeader = {
  fontSize: 9,
  fontWeight: 600,
  color: 'var(--text-dim)',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
  marginBottom: 8,
  marginTop: 16,
  fontFamily: 'var(--font-mono)',
};

const card = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  padding: '8px 10px',
  marginBottom: 6,
  cursor: 'pointer',
  transition: 'background 150ms ease',
  fontFamily: 'var(--font-mono)',
};

function Sidebar({ scanData, activeView, setActiveView, onSelectModule, selectedModule }) {
  const { metadata, files, edges, issues, env_vars, entry_points, modules } = scanData;

  const codeFiles = files.filter(f => ['.py', '.js', '.jsx', '.ts', '.tsx'].includes(f.extension));
  const configFiles = files.filter(f => f.status === 'config');
  const docFiles = files.filter(f => f.status === 'documentation');
  const buildFiles = files.filter(f => f.status === 'build');

  const orphanCount = issues?.orphans?.length || 0;
  const deadCount = issues?.dead_imports?.length || 0;
  const circularCount = issues?.circular?.length || 0;
  const runtimeCircular = issues?.circular?.filter(c => c.severity === 'runtime').length || 0;

  // Count hotspot files (files with high hotspot score)
  const hotspotFiles = files.filter(f => f.git?.hotspot_score > 10);

  return (
    <div style={{
      width: 'var(--sidebar-width)',
      minWidth: 'var(--sidebar-width)',
      height: '100%',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border)',
      overflowY: 'auto',
      padding: '12px 14px',
      fontFamily: 'var(--font-mono)',
    }}>
      {/* SCAN INFO */}
      <div style={sectionHeader}>Scan Info</div>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 4 }}>
        {truncatePath(metadata.scanned_path, 30)}
      </div>
      <div style={{ fontSize: 9, color: 'var(--text-dim)', marginBottom: 8 }}>
        {new Date(metadata.timestamp).toLocaleString()}
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <StatBadge label="Files" value={metadata.total_files} />
        <StatBadge label="LOC" value={formatLOC(metadata.total_loc)} />
        <StatBadge label="Modules" value={metadata.total_modules} />
      </div>
      {/* File type bar */}
      <FileTypeBar code={codeFiles.length} config={configFiles.length} docs={docFiles.length} build={buildFiles.length} total={files.length} />

      {/* HEALTH OVERVIEW */}
      <div style={sectionHeader}>Health Overview</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        <HealthCard label="Orphans" value={orphanCount} color={orphanCount > 0 ? 'var(--status-error)' : 'var(--status-ok)'} />
        <HealthCard label="Dead Imports" value={deadCount} color={deadCount > 0 ? 'var(--status-error)' : 'var(--status-ok)'} />
        <HealthCard label="Circular" value={circularCount} color={circularCount > 0 ? 'var(--status-warn)' : 'var(--status-ok)'}
          detail={runtimeCircular > 0 ? `${runtimeCircular} runtime` : null} />
        <HealthCard label="Hotspots" value={hotspotFiles.length} color={hotspotFiles.length > 5 ? 'var(--status-warn)' : 'var(--text-secondary)'} />
        <HealthCard label="Entry Points" value={entry_points?.length || 0} color="var(--status-info)" />
      </div>

      {/* ISSUES */}
      <div style={sectionHeader}>Issues</div>
      <ExpandableList
        title={`Dead Imports (${deadCount})`}
        items={(issues?.dead_imports || []).map(d => ({
          label: `${shortPath(d.file)}: ${d.symbol || d.imports}`,
          detail: d.reason,
          onClick: () => {
            const mod = files.find(f => f.path === d.file)?.module;
            if (mod) onSelectModule(mod);
          }
        }))}
      />
      <ExpandableList
        title={`Orphans (${orphanCount})`}
        items={(issues?.orphans || []).map(o => ({
          label: o,
          onClick: () => {
            const mod = files.find(f => f.path === o)?.module;
            if (mod) onSelectModule(mod);
          }
        }))}
      />
      <ExpandableList
        title={`Circular Deps (${circularCount})`}
        items={(issues?.circular || []).map(c => ({
          label: c.cycle.map(shortPath).join(' → '),
          detail: c.severity,
          color: c.severity === 'runtime' ? 'var(--status-error)' : 'var(--status-warn)',
        }))}
      />

      {/* ENV VARS */}
      <div style={sectionHeader}>Env Vars ({env_vars?.length || 0})</div>
      <ExpandableList
        title="Environment Variables"
        defaultOpen={false}
        items={(env_vars || []).map(ev => ({
          label: ev.name,
          detail: `${ev.referenced_by.length} files`,
          onClick: () => {
            // Highlight first module referencing it
            const file = files.find(f => ev.referenced_by.includes(f.path));
            if (file) onSelectModule(file.module);
          }
        }))}
      />

      {/* LEGEND */}
      <div style={sectionHeader}>Legend</div>
      <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>
        {Object.entries(getUniqueModuleColors(modules)).map(([name, color]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
            <span>{name}</span>
          </div>
        ))}
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 16, height: 0, borderTop: '2px solid var(--text-dim)' }} />
            <span>strong</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 16, height: 0, borderTop: '2px dashed var(--text-dim)' }} />
            <span>lazy</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 16, height: 0, borderTop: '2px dotted var(--text-dim)' }} />
            <span>conditional</span>
          </div>
        </div>
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-ok)' }} />
            <span>healthy</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-warn)' }} />
            <span>dead imports</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-error)' }} />
            <span>orphans</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-dim)' }} />
            <span>data/config</span>
          </div>
        </div>
      </div>

      {/* VIEW TOGGLE */}
      <div style={sectionHeader}>View</div>
      <div style={{ display: 'flex', gap: 4 }}>
        <button
          onClick={() => setActiveView('graph')}
          style={{
            ...toggleBtn,
            background: activeView === 'graph' ? 'var(--bg-card)' : 'transparent',
            color: activeView === 'graph' ? 'var(--text-primary)' : 'var(--text-dim)',
          }}
        >
          Graph
        </button>
        <button
          onClick={() => setActiveView('dashboard')}
          style={{
            ...toggleBtn,
            background: activeView === 'dashboard' ? 'var(--bg-card)' : 'transparent',
            color: activeView === 'dashboard' ? 'var(--text-primary)' : 'var(--text-dim)',
          }}
        >
          Dashboard
        </button>
      </div>

      {/* Keyboard hints */}
      <div style={{ marginTop: 16, fontSize: 9, color: 'var(--text-dim)', lineHeight: 1.8 }}>
        <div><kbd style={kbd}>Esc</kbd> clear selection</div>
        <div><kbd style={kbd}>F</kbd> fit viewport</div>
        <div><kbd style={kbd}>D</kbd> toggle view</div>
        <div><kbd style={kbd}>/</kbd> focus search</div>
      </div>
    </div>
  );
}

const toggleBtn = {
  flex: 1,
  padding: '6px 0',
  border: '1px solid var(--border)',
  borderRadius: 4,
  fontSize: 10,
  fontFamily: 'var(--font-mono)',
  cursor: 'pointer',
  transition: 'all 150ms ease',
};

const kbd = {
  display: 'inline-block',
  padding: '1px 4px',
  border: '1px solid var(--border)',
  borderRadius: 3,
  fontSize: 9,
  fontFamily: 'var(--font-mono)',
  marginRight: 4,
  color: 'var(--text-secondary)',
};

function StatBadge({ label, value }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 4,
      padding: '4px 8px',
      fontSize: 10,
    }}>
      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{value}</span>
      <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>{label}</span>
    </div>
  );
}

function HealthCard({ label, value, color, detail, onClick }) {
  return (
    <div
      style={{
        ...card,
        textAlign: 'center',
      }}
      onClick={onClick}
    >
      <div style={{ fontSize: 16, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>{label}</div>
      {detail && <div style={{ fontSize: 8, color: 'var(--status-error)', marginTop: 2 }}>{detail}</div>}
    </div>
  );
}

function FileTypeBar({ code, config, docs, build, total }) {
  if (total === 0) return null;
  const segments = [
    { count: code, color: 'var(--status-info)', label: 'code' },
    { count: config, color: 'var(--status-warn)', label: 'config' },
    { count: docs, color: 'var(--status-ok)', label: 'docs' },
    { count: build, color: 'var(--text-dim)', label: 'build' },
    { count: total - code - config - docs - build, color: 'var(--border)', label: 'other' },
  ].filter(s => s.count > 0);

  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', height: 4, borderRadius: 2, overflow: 'hidden', gap: 1 }}>
        {segments.map(s => (
          <div
            key={s.label}
            style={{
              width: `${(s.count / total) * 100}%`,
              background: s.color,
              minWidth: 2,
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 9, color: 'var(--text-dim)' }}>
        {segments.map(s => (
          <span key={s.label}>{s.count} {s.label}</span>
        ))}
      </div>
    </div>
  );
}

function ExpandableList({ title, items, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  if (!items || items.length === 0) return null;

  return (
    <div style={{ marginBottom: 6 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          fontSize: 10,
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          padding: '4px 0',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        <span style={{ fontSize: 8, transition: 'transform 150ms', transform: open ? 'rotate(90deg)' : 'rotate(0)' }}>▶</span>
        {title}
      </div>
      {open && (
        <div style={{ paddingLeft: 12 }}>
          {items.map((item, i) => (
            <div
              key={i}
              onClick={item.onClick}
              style={{
                fontSize: 9,
                color: item.color || 'var(--text-dim)',
                padding: '2px 0',
                cursor: item.onClick ? 'pointer' : 'default',
                transition: 'color 150ms ease',
              }}
            >
              {item.label}
              {item.detail && (
                <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>({item.detail})</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function truncatePath(p, maxLen) {
  if (p.length <= maxLen) return p;
  return '...' + p.slice(-(maxLen - 3));
}

function shortPath(p) {
  const parts = p.split('/');
  return parts.length > 2 ? parts.slice(-2).join('/') : p;
}

function formatLOC(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

function getUniqueModuleColors(modules) {
  const colorMap = {};
  const seen = new Set();
  for (const m of modules) {
    const color = getModuleColor(m.name);
    const key = color.border;
    if (!seen.has(key)) {
      seen.add(key);
      // Use first module with this color as label
      colorMap[m.name] = key;
    }
  }
  // Only show first 12
  const entries = Object.entries(colorMap);
  const result = {};
  for (const [name, color] of entries.slice(0, 12)) {
    result[name] = color;
  }
  return result;
}

export default memo(Sidebar);
