import { memo } from 'react';
import { getModuleColor, getModuleStatus } from '../utils/colors';

function DetailPanel({ scanData, selectedModule, selectedFile, onSelectModule, onSelectFile, onClose }) {
  const { modules, files, edges, issues } = scanData;

  const moduleData = selectedModule ? modules.find(m => m.name === selectedModule) : null;
  const fileData = selectedFile ? files.find(f => f.path === selectedFile) : null;

  return (
    <div style={{
      width: 320,
      minWidth: 320,
      height: '100%',
      background: 'var(--bg-secondary)',
      borderLeft: '1px solid var(--border)',
      overflowY: 'auto',
      padding: '12px 14px',
      fontFamily: 'var(--font-mono)',
      animation: 'slide-in-right 200ms ease',
    }}>
      {/* Close button */}
      <div
        onClick={onClose}
        style={{
          position: 'sticky',
          top: 0,
          float: 'right',
          width: 24,
          height: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          color: 'var(--text-dim)',
          fontSize: 14,
          borderRadius: 4,
          transition: 'color 150ms',
          zIndex: 10,
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
      >
        ×
      </div>

      {fileData ? (
        <FileDetail file={fileData} scanData={scanData} onSelectModule={onSelectModule} onSelectFile={onSelectFile} />
      ) : moduleData ? (
        <ModuleDetail module={moduleData} scanData={scanData} onSelectModule={onSelectModule} onSelectFile={onSelectFile} />
      ) : null}
    </div>
  );
}

function ModuleDetail({ module, scanData, onSelectModule, onSelectFile }) {
  const color = getModuleColor(module.name);
  const status = getModuleStatus(module, scanData.files, scanData.issues);
  const moduleFiles = scanData.files
    .filter(f => f.module === module.name)
    .sort((a, b) => b.loc - a.loc);

  // Find imports and imported-by modules
  const importsModules = new Set();
  const importedByModules = new Set();
  const fileToModule = new Map();
  for (const f of scanData.files) {
    fileToModule.set(f.path, f.module);
  }
  for (const edge of scanData.edges) {
    const srcMod = fileToModule.get(edge.from);
    const tgtMod = fileToModule.get(edge.to);
    if (srcMod === module.name && tgtMod !== module.name) {
      importsModules.add(tgtMod);
    }
    if (tgtMod === module.name && srcMod !== module.name) {
      importedByModules.add(srcMod);
    }
  }

  // Dead imports in this module
  const deadImports = (scanData.issues?.dead_imports || []).filter(d =>
    moduleFiles.some(f => f.path === d.file)
  );

  // Orphan files in this module
  const orphanFiles = (scanData.issues?.orphans || []).filter(o =>
    moduleFiles.some(f => f.path === o)
  );

  // Git stats
  const totalChanges = moduleFiles.reduce((sum, f) => sum + (f.git?.change_count || 0), 0);
  const mostActive = moduleFiles.reduce((best, f) =>
    (f.git?.change_count || 0) > (best?.git?.change_count || 0) ? f : best
  , moduleFiles[0]);

  const health = module.health || {};

  return (
    <div>
      <div style={{ fontSize: 16, fontWeight: 600, color: color.text, marginBottom: 4 }}>
        {module.name}
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 12 }}>{module.path || '(root)'}</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 16 }}>
        <MetricCard label="Files" value={module.file_count} />
        <MetricCard label="LOC" value={formatLOC(module.total_loc)} />
        <MetricCard label="Cohesion" value={`${(health.cohesion * 100).toFixed(0)}%`}
          color={health.cohesion > 0.5 ? 'var(--status-ok)' : health.cohesion > 0.2 ? 'var(--status-warn)' : 'var(--status-error)'} />
        <MetricCard label="Coupling" value={health.coupling}
          color={health.coupling > 10 ? 'var(--status-error)' : health.coupling > 5 ? 'var(--status-warn)' : 'var(--status-ok)'} />
        <MetricCard label="Avg Complex." value={health.avg_complexity?.toFixed(1)} />
        <MetricCard label="Hottest" value={health.hottest_file || '-'} small />
      </div>

      {totalChanges > 0 && (
        <>
          <SectionLabel>Git Activity</SectionLabel>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 12 }}>
            <div>{totalChanges} total changes</div>
            {mostActive && <div>Most active: {mostActive.name}</div>}
          </div>
        </>
      )}

      <SectionLabel>Files ({moduleFiles.length})</SectionLabel>
      <div style={{ marginBottom: 12 }}>
        {moduleFiles.map(f => {
          const hasDead = scanData.issues?.dead_imports?.some(d => d.file === f.path);
          const dotColor = f.status === 'entry_point' ? 'var(--status-info)'
            : hasDead ? 'var(--status-error)'
            : f.status === 'code_orphan' ? 'var(--status-error)'
            : 'var(--text-dim)';

          return (
            <div
              key={f.path}
              onClick={() => onSelectFile(f.path)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 0',
                cursor: 'pointer',
                fontSize: 10,
                color: 'var(--text-secondary)',
                transition: 'color 150ms',
              }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
            >
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
              <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>{f.loc}</span>
              <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>C{f.metrics?.cyclomatic_complexity || 0}</span>
              {f.git?.change_count > 0 && (
                <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>Δ{f.git.change_count}</span>
              )}
            </div>
          );
        })}
      </div>

      {importsModules.size > 0 && (
        <>
          <SectionLabel>Imports ({importsModules.size})</SectionLabel>
          <ModuleList modules={importsModules} onSelectModule={onSelectModule} scanData={scanData} />
        </>
      )}

      {importedByModules.size > 0 && (
        <>
          <SectionLabel>Imported By ({importedByModules.size})</SectionLabel>
          <ModuleList modules={importedByModules} onSelectModule={onSelectModule} scanData={scanData} />
        </>
      )}

      {deadImports.length > 0 && (
        <>
          <SectionLabel color="var(--status-error)">Dead Imports ({deadImports.length})</SectionLabel>
          {deadImports.map((d, i) => (
            <div key={i} style={{ fontSize: 9, color: 'var(--status-error)', padding: '2px 0' }}>
              {d.file}: {d.symbol || d.imports}
              <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>({d.reason})</span>
            </div>
          ))}
        </>
      )}

      {orphanFiles.length > 0 && (
        <>
          <SectionLabel color="var(--status-error)">Orphan Files ({orphanFiles.length})</SectionLabel>
          {orphanFiles.map((o, i) => (
            <div key={i} style={{ fontSize: 9, color: 'var(--status-error)', padding: '2px 0' }}>{o}</div>
          ))}
        </>
      )}
    </div>
  );
}

function FileDetail({ file, scanData, onSelectModule, onSelectFile }) {
  const metrics = file.metrics || {};
  const git = file.git || {};

  // Find imports
  const fileEdges = scanData.edges.filter(e => e.from === file.path);
  const importedByEdges = scanData.edges.filter(e => e.to === file.path);

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4, wordBreak: 'break-all' }}>
        {file.name}
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4 }}>{file.path}</div>
      <StatusBadge status={file.status} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 16, marginTop: 12 }}>
        <MetricCard label="LOC" value={file.loc} />
        <MetricCard label="Extension" value={file.extension} />
        <MetricCard label="Functions" value={metrics.function_count} />
        <MetricCard label="Classes" value={metrics.class_count} />
        <MetricCard label="Complexity" value={metrics.cyclomatic_complexity}
          color={metrics.cyclomatic_complexity > 50 ? 'var(--status-error)' : metrics.cyclomatic_complexity > 20 ? 'var(--status-warn)' : 'var(--status-ok)'} />
        <MetricCard label="Exports" value={metrics.export_count} />
      </div>

      {(git.change_count > 0 || git.last_modified) && (
        <>
          <SectionLabel>Git</SectionLabel>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 12 }}>
            {git.change_count > 0 && <div>Changes: {git.change_count}</div>}
            {git.last_modified && <div>Last modified: {git.last_modified}</div>}
            {git.contributors > 0 && <div>Contributors: {git.contributors}</div>}
            {git.hotspot_score > 0 && <div>Hotspot score: {git.hotspot_score}</div>}
          </div>
        </>
      )}

      {file.exports && file.exports.length > 0 && (
        <>
          <SectionLabel>Exports ({file.exports.length})</SectionLabel>
          <div style={{ marginBottom: 12 }}>
            {file.exports.map((exp, i) => (
              <div key={i} style={{ fontSize: 9, color: 'var(--text-secondary)', padding: '2px 0' }}>
                <span style={{ color: exp.type === 'function' ? 'var(--status-info)' : exp.type === 'class' ? 'var(--text-secondary)' : 'var(--text-primary)' }}>
                  {exp.type}
                </span>{' '}
                {exp.name}
                <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>:{exp.line_number}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {fileEdges.length > 0 && (
        <>
          <SectionLabel>Imports ({fileEdges.length})</SectionLabel>
          <div style={{ marginBottom: 12 }}>
            {fileEdges.map((e, i) => (
              <div
                key={i}
                onClick={() => onSelectFile(e.to)}
                style={{
                  fontSize: 9,
                  color: 'var(--text-secondary)',
                  padding: '2px 0',
                  cursor: 'pointer',
                }}
              >
                <span style={{ color: edgeTypeColor(e.type) }}>{e.type}</span>{' '}
                {shortPath(e.to)}
                {e.imported_names?.length > 0 && (
                  <span style={{ color: 'var(--text-dim)' }}> ({e.imported_names.join(', ')})</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {importedByEdges.length > 0 && (
        <>
          <SectionLabel>Imported By ({importedByEdges.length})</SectionLabel>
          <div style={{ marginBottom: 12 }}>
            {importedByEdges.map((e, i) => (
              <div
                key={i}
                onClick={() => onSelectFile(e.from)}
                style={{ fontSize: 9, color: 'var(--text-secondary)', padding: '2px 0', cursor: 'pointer' }}
              >
                {shortPath(e.from)}
              </div>
            ))}
          </div>
        </>
      )}

      <div style={{ marginTop: 8 }}>
        <button
          onClick={() => onSelectModule(file.module)}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            padding: '6px 10px',
            color: 'var(--text-secondary)',
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            cursor: 'pointer',
          }}
        >
          ← Back to {file.module}
        </button>
      </div>
    </div>
  );
}

function ModuleList({ modules, onSelectModule, scanData }) {
  return (
    <div style={{ marginBottom: 12 }}>
      {[...modules].sort().map(name => {
        const color = getModuleColor(name);
        return (
          <div
            key={name}
            onClick={() => onSelectModule(name)}
            style={{
              fontSize: 10,
              color: color.text,
              padding: '3px 0',
              cursor: 'pointer',
            }}
          >
            {name}
          </div>
        );
      })}
    </div>
  );
}

function MetricCard({ label, value, color, small }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 4,
      padding: '6px 8px',
    }}>
      <div style={{
        fontSize: small ? 9 : 13,
        fontWeight: 600,
        color: color || 'var(--text-primary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {value ?? '-'}
      </div>
      <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function SectionLabel({ children, color }) {
  return (
    <div style={{
      fontSize: 9,
      fontWeight: 600,
      color: color || 'var(--text-dim)',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      marginBottom: 6,
      marginTop: 12,
    }}>
      {children}
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    active: 'var(--status-ok)',
    entry_point: 'var(--status-info)',
    code_orphan: 'var(--status-error)',
    config: 'var(--status-warn)',
    documentation: 'var(--text-dim)',
    data: 'var(--text-dim)',
    build: 'var(--text-dim)',
    asset: 'var(--text-dim)',
    namespace: 'var(--text-dim)',
  };

  return (
    <span style={{
      display: 'inline-block',
      fontSize: 9,
      padding: '2px 6px',
      borderRadius: 3,
      color: colors[status] || 'var(--text-dim)',
      border: `1px solid ${colors[status] || 'var(--border)'}`,
    }}>
      {status}
    </span>
  );
}

function edgeTypeColor(type) {
  switch (type) {
    case 'strong': return 'var(--text-secondary)';
    case 'lazy': return 'var(--status-warn)';
    case 'conditional': return 'var(--text-dim)';
    case 'type_only': return 'var(--text-dim)';
    default: return 'var(--text-dim)';
  }
}

function shortPath(p) {
  const parts = p.split('/');
  return parts.length > 2 ? parts.slice(-2).join('/') : p;
}

function formatLOC(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

export default memo(DetailPanel);
