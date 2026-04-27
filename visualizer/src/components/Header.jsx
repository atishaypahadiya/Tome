import { memo } from 'react';

const styles = {
  header: {
    height: 'var(--header-height)',
    minHeight: 'var(--header-height)',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    fontFamily: 'var(--font-mono)',
    zIndex: 100,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: 'var(--status-ok)',
    animation: 'pulse-dot 3s infinite',
    color: 'var(--status-ok)',
  },
  projectName: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
    letterSpacing: '0.02em',
  },
  label: {
    fontSize: 10,
    color: 'var(--text-dim)',
    marginLeft: 4,
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  stat: {
    fontSize: 10,
    color: 'var(--text-secondary)',
  },
  statValue: {
    color: 'var(--text-primary)',
    fontWeight: 600,
  },
  separator: {
    color: 'var(--text-dim)',
    fontSize: 10,
  },
  issueCount: (color) => ({
    color,
    fontWeight: 600,
    fontSize: 10,
  }),
};

function Header({ scanData }) {
  const { metadata, edges, issues } = scanData;
  const projectName = metadata.scanned_path.split('/').filter(Boolean).pop()?.toUpperCase() || 'PROJECT';

  const edgeTypes = {};
  for (const e of edges) {
    edgeTypes[e.type] = (edgeTypes[e.type] || 0) + 1;
  }

  const orphanCount = issues?.orphans?.length || 0;
  const deadCount = issues?.dead_imports?.length || 0;
  const circularCount = issues?.circular?.length || 0;

  return (
    <div style={styles.header}>
      <div style={styles.left}>
        <div style={styles.dot} />
        <span style={styles.projectName}>{projectName}</span>
        <span style={styles.label}>Tome</span>
      </div>
      <div style={styles.right}>
        <span style={styles.stat}>
          <span style={styles.statValue}>{metadata.total_files}</span> files
        </span>
        <span style={styles.stat}>
          <span style={styles.statValue}>{formatLOC(metadata.total_loc)}</span> LOC
        </span>
        <span style={styles.stat}>
          <span style={styles.statValue}>{metadata.total_modules}</span> modules
        </span>
        <span style={styles.separator}>|</span>
        <span style={styles.stat}>
          {edgeTypes.strong || 0} strong
          <span style={styles.separator}> · </span>
          {edgeTypes.lazy || 0} lazy
          <span style={styles.separator}> · </span>
          {edgeTypes.conditional || 0} conditional
        </span>
        <span style={styles.separator}>|</span>
        {orphanCount > 0 && (
          <span style={styles.issueCount('var(--status-error)')}>
            {orphanCount} orphan{orphanCount !== 1 ? 's' : ''}
          </span>
        )}
        {deadCount > 0 && (
          <span style={styles.issueCount('var(--status-warn)')}>
            {deadCount} dead
          </span>
        )}
        {circularCount > 0 && (
          <span style={styles.issueCount('var(--status-warn)')}>
            {circularCount} circular
          </span>
        )}
        {orphanCount === 0 && deadCount === 0 && circularCount === 0 && (
          <span style={styles.issueCount('var(--status-ok)')}>clean</span>
        )}
      </div>
    </div>
  );
}

function formatLOC(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

export default memo(Header);
