import { memo } from 'react';

const btn = {
  width: 28,
  height: 28,
  borderRadius: 14,
  background: 'rgba(8, 12, 20, 0.5)',
  backdropFilter: 'blur(12px)',
  border: '1px solid rgba(60, 80, 110, 0.15)',
  color: 'var(--text-dim)',
  fontSize: 10,
  fontFamily: 'var(--font-mono)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 150ms',
};

const btnActive = {
  ...btn,
  background: 'rgba(14, 20, 32, 0.85)',
  color: 'var(--text-primary)',
  borderColor: 'rgba(120, 152, 184, 0.3)',
};

function FloatingButtons({
  showHeader,
  showSidebar,
  showDashboard,
  onToggleHeader,
  onToggleSidebar,
  onToggleDashboard,
  onToggleSimBar,
  onFitViewport,
}) {
  return (
    <>
      <div style={{ position: 'absolute', top: 12, left: 12, display: 'flex', gap: 6, zIndex: 50 }}>
        <button
          style={showHeader ? btnActive : btn}
          onClick={onToggleHeader}
          title="Toggle header (H)"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(14, 20, 32, 0.85)'; }}
          onMouseLeave={e => { if (!showHeader) { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.background = btn.background; }}}
        >
          H
        </button>
        <button
          style={showSidebar ? btnActive : btn}
          onClick={onToggleSidebar}
          title="Toggle sidebar (S)"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(14, 20, 32, 0.85)'; }}
          onMouseLeave={e => { if (!showSidebar) { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.background = btn.background; }}}
        >
          S
        </button>
        <button
          style={showDashboard ? btnActive : btn}
          onClick={onToggleDashboard}
          title="Toggle dashboard (D)"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(14, 20, 32, 0.85)'; }}
          onMouseLeave={e => { if (!showDashboard) { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.background = btn.background; }}}
        >
          D
        </button>
      </div>
      <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 6, zIndex: 50 }}>
        <button
          style={btn}
          onClick={onFitViewport}
          title="Fit viewport (F)"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(14, 20, 32, 0.85)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.background = btn.background; }}
        >
          F
        </button>
      </div>
      <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 50 }}>
        <button
          style={btn}
          onClick={onToggleSimBar}
          title="Search (/)"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(14, 20, 32, 0.85)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.background = btn.background; }}
        >
          /
        </button>
      </div>
    </>
  );
}

export default memo(FloatingButtons);
