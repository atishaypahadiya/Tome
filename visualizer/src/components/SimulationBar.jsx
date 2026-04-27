import { memo, useState, useRef, useEffect, useCallback } from 'react';

function SimulationBar({ modules, edges, onSimulate, onClear, simulationActive }) {
  const [input, setInput] = useState('');
  const [source, setSource] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef(null);

  const moduleNames = modules.map(m => m.name).sort();

  const updateSuggestions = useCallback((query) => {
    if (!query) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    const q = query.toLowerCase();
    const filtered = moduleNames.filter(n => n.toLowerCase().includes(q));
    setSuggestions(filtered.slice(0, 8));
    setShowSuggestions(filtered.length > 0);
    setSelectedIndex(0);
  }, [moduleNames]);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setInput(val);

    // If we already have a source, filter for target
    const queryPart = source ? val : val;
    updateSuggestions(queryPart);
  };

  const selectModule = (name) => {
    if (!source) {
      setSource(name);
      setInput('');
      setSuggestions([]);
      setShowSuggestions(false);
    } else {
      // We have source, this is target
      onSimulate(source, name);
      setInput('');
      setSource(null);
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (suggestions.length > 0 && showSuggestions) {
        selectModule(suggestions[selectedIndex]);
      } else if (source && !input) {
        // Single module simulation
        onSimulate(source, null);
        setSource(null);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      if (source) {
        setSource(null);
        setInput('');
      }
    } else if (e.key === 'Backspace' && input === '' && source) {
      setSource(null);
    }
  };

  const handleClear = () => {
    setInput('');
    setSource(null);
    setSuggestions([]);
    setShowSuggestions(false);
    onClear();
  };

  const placeholder = source
    ? `target... (or Enter to trace all from ${shortName(source)})`
    : 'trace a path... (e.g., backend/routes → backend/core)';

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 50,
    }}>
      {/* Suggestions dropdown */}
      {showSuggestions && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: 0,
          right: 0,
          marginBottom: 4,
          background: 'rgba(8, 12, 20, 0.96)',
          border: '1px solid rgba(60, 80, 110, 0.2)',
          borderRadius: 12,
          overflow: 'hidden',
          backdropFilter: 'blur(16px)',
        }}>
          {suggestions.map((name, i) => (
            <div
              key={name}
              onClick={() => selectModule(name)}
              style={{
                padding: '6px 16px',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: i === selectedIndex ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: i === selectedIndex ? 'rgba(14, 20, 32, 0.8)' : 'transparent',
                cursor: 'pointer',
                transition: 'background 100ms',
              }}
              onMouseEnter={() => setSelectedIndex(i)}
            >
              <HighlightMatch text={name} query={input} />
            </div>
          ))}
        </div>
      )}

      {/* Main bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        width: 600,
        height: 48,
        background: 'rgba(8, 12, 20, 0.88)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(60, 80, 110, 0.2)',
        borderRadius: 24,
        padding: '0 20px',
        gap: 8,
      }}>
        {/* Source badge */}
        {source && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '3px 8px',
            background: 'rgba(120, 152, 184, 0.12)',
            border: '1px solid rgba(120, 152, 184, 0.25)',
            borderRadius: 12,
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            color: 'var(--status-info)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}>
            {shortName(source)}
            <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>→</span>
          </div>
        )}

        <input
          ref={inputRef}
          data-simulation-input
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => input && updateSuggestions(input)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder={placeholder}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: 13,
            fontFamily: 'var(--font-mono)',
          }}
        />

        {simulationActive && (
          <button
            onClick={handleClear}
            style={{
              background: 'rgba(176, 136, 136, 0.12)',
              border: '1px solid rgba(176, 136, 136, 0.25)',
              borderRadius: 12,
              padding: '3px 10px',
              color: 'var(--status-error)',
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

function HighlightMatch({ text, query }) {
  if (!query) return <span>{text}</span>;

  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  const idx = lower.indexOf(q);

  if (idx === -1) return <span>{text}</span>;

  return (
    <span>
      {text.slice(0, idx)}
      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </span>
  );
}

function shortName(name) {
  const parts = name.split('/');
  return parts.length > 2 ? parts.slice(-2).join('/') : name;
}

export default memo(SimulationBar);
