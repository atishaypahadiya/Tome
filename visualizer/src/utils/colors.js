// Monochromatic space-tech palette
// Modules are differentiated by brightness/warmth, not hue
// White → light grey → silver → cool grey spectrum

const MODULE_PALETTE = [
  { fill: '#ffffff', glow: '#ffffff' },   // pure white (entry points, core)
  { fill: '#e8ecf1', glow: '#d0d8e4' },   // ice white
  { fill: '#c8d1dc', glow: '#b0bccb' },   // silver
  { fill: '#a0adb8', glow: '#8a9aaa' },   // cool grey
  { fill: '#7b8fa0', glow: '#6b7f90' },   // steel
  { fill: '#dfe4ea', glow: '#c4cdd6' },   // light frost
  { fill: '#b8c4d0', glow: '#9aabb8' },   // mist
  { fill: '#f0f2f5', glow: '#d8dce2' },   // ghost white
  { fill: '#8ea0b0', glow: '#7890a0' },   // slate
  { fill: '#d5dbe2', glow: '#bcc5d0' },   // pearl
  { fill: '#94a8b8', glow: '#7e96a8' },   // ash
  { fill: '#e2e6eb', glow: '#cad0d8' },   // cloud
];

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

const moduleColorCache = new Map();

export function getModuleColor(moduleName) {
  if (moduleColorCache.has(moduleName)) return moduleColorCache.get(moduleName);

  const h = hashString(moduleName);
  const palette = MODULE_PALETTE[h % MODULE_PALETTE.length];
  const result = { border: palette.fill, text: palette.fill, glow: palette.glow };
  moduleColorCache.set(moduleName, result);
  return result;
}

export function getStatusColor(status) {
  switch (status) {
    case 'healthy': return '#8aacca';
    case 'warning': return '#a09488';
    case 'error': return '#b08888';
    case 'inactive': return '#2e3848';
    default: return '#2e3848';
  }
}

export function getModuleStatus(moduleData, files, issues) {
  const moduleFiles = files.filter(f => f.module === moduleData.name);
  const hasDeadImports = issues?.dead_imports?.some(d =>
    moduleFiles.some(f => f.path === d.file)
  );
  const hasOrphans = issues?.orphans?.some(o =>
    moduleFiles.some(f => f.path === o)
  );

  const isDataOnly = moduleFiles.every(f =>
    ['config', 'data', 'documentation', 'build', 'asset', 'namespace'].includes(f.status)
  );

  if (isDataOnly) return 'inactive';
  if (hasOrphans) return 'error';
  if (hasDeadImports) return 'warning';
  return 'healthy';
}

export const EDGE_STYLES = {
  strong: { dash: 'none', opacity: 0.15, color: 'rgba(255,255,255,0.12)' },
  lazy: { dash: '8 4', opacity: 0.08, color: 'rgba(255,255,255,0.08)' },
  conditional: { dash: '3 3', opacity: 0.06, color: 'rgba(255,255,255,0.06)' },
  type_only: { dash: '2 4', opacity: 0.03, color: 'rgba(255,255,255,0.03)' },
};
