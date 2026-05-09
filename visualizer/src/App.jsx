import { useState, useEffect, useCallback, useMemo } from 'react';
import { validateScanData, FALLBACK_DATA } from './data/sampleData';
import { computeLayout } from './utils/layout';
import { useForceSimulation } from './hooks/useForceSimulation';
import { useSimulation } from './hooks/useSimulation';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import GraphView from './components/GraphView';
import DetailPanel from './components/DetailPanel';
import SimulationBar from './components/SimulationBar';
import Dashboard from './components/Dashboard';
import FileDropZone from './components/FileDropZone';
import FloatingButtons from './components/FloatingButtons';

export default function App() {
  const [scanData, setScanData] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);
  const [hoveredFile, setHoveredFile] = useState(null);

  // Panel visibility — all hidden by default
  const [showHeader, setShowHeader] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [showSimBar, setShowSimBar] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);

  // Load scan data: prefer the live API (served by `tome view`),
  // fall back to bundled sample data (so `npm run dev` works standalone).
  useEffect(() => {
    const tryLoad = async () => {
      const apiRes = await fetch('/api/scan-data.json').catch(() => null);
      if (apiRes && apiRes.ok) {
        const data = await apiRes.json();
        if (validateScanData(data)) {
          setScanData(data);
          return;
        }
      }
      const sampleRes = await fetch('/sample-data.json').catch(() => null);
      if (sampleRes && sampleRes.ok) {
        const data = await sampleRes.json();
        if (validateScanData(data)) {
          setScanData(data);
          return;
        }
      }
      setScanData(FALLBACK_DATA);
    };
    tryLoad();
  }, []);

  // Compute file-level layout
  const { nodes, edges, modules: layoutModules } = useMemo(
    () => scanData ? computeLayout(scanData) : { nodes: [], edges: [], modules: [] },
    [scanData]
  );

  // Force simulation
  const { simulationRef, setTickCallback, reheat } = useForceSimulation(nodes, edges);

  // Module-level edges for path simulation
  const moduleEdges = useMemo(() => {
    if (!scanData) return [];
    const fileToModule = new Map();
    for (const f of scanData.files) fileToModule.set(f.path, f.module);
    const edgeMap = new Map();
    for (const e of scanData.edges) {
      const sm = fileToModule.get(e.from);
      const tm = fileToModule.get(e.to);
      if (!sm || !tm || sm === tm) continue;
      const key = `${sm}|${tm}`;
      if (!edgeMap.has(key)) edgeMap.set(key, { source: sm, target: tm, weight: 0, types: new Set(), fileEdges: [] });
      const me = edgeMap.get(key);
      me.weight++;
      me.types.add(e.type);
      me.fileEdges.push(e);
    }
    return [...edgeMap.values()];
  }, [scanData]);

  const { simulationPath, simulationEdges, startSimulation, clearSimulation } = useSimulation(moduleEdges);

  const handleFileDrop = useCallback((data) => {
    if (validateScanData(data)) {
      setScanData(data);
      setSelectedFile(null);
      setSelectedModule(null);
      setShowDetail(false);
      clearSimulation();
    }
  }, [clearSimulation]);

  const handleSelectFile = useCallback((filePath) => {
    if (selectedFile === filePath) {
      setSelectedFile(null);
      setSelectedModule(null);
      setShowDetail(false);
    } else {
      setSelectedFile(filePath);
      const file = scanData?.files.find(f => f.path === filePath);
      if (file) setSelectedModule(file.module);
      setShowDetail(true);
    }
  }, [selectedFile, scanData]);

  const handleSelectModule = useCallback((moduleName) => {
    setSelectedModule(prev => prev === moduleName ? null : moduleName);
    setSelectedFile(null);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedFile(null);
    setSelectedModule(null);
    setShowDetail(false);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      switch (e.key) {
        case 'Escape':
          setSelectedFile(null);
          setSelectedModule(null);
          setShowDetail(false);
          setShowSimBar(false);
          clearSimulation();
          break;
        case 'f':
          window.dispatchEvent(new CustomEvent('tome:fit-viewport'));
          break;
        case 'h':
          setShowHeader(prev => !prev);
          break;
        case 's':
          setShowSidebar(prev => !prev);
          break;
        case 'd':
          setShowDashboard(prev => !prev);
          break;
        case '/':
          e.preventDefault();
          setShowSimBar(true);
          setTimeout(() => document.querySelector('[data-simulation-input]')?.focus(), 100);
          break;
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [clearSimulation]);

  if (!scanData) return null;

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* Graph takes full screen */}
      <GraphView
        nodes={nodes}
        edges={edges}
        scanData={scanData}
        selectedFile={selectedFile}
        hoveredFile={hoveredFile}
        simulationRef={simulationRef}
        setTickCallback={setTickCallback}
        simulationPath={simulationPath}
        onSelectFile={handleSelectFile}
        onHoverFile={setHoveredFile}
        onBackgroundClick={handleBackgroundClick}
      />

      {/* Floating toggle buttons */}
      <FloatingButtons
        showHeader={showHeader}
        showSidebar={showSidebar}
        showDashboard={showDashboard}
        onToggleHeader={() => setShowHeader(p => !p)}
        onToggleSidebar={() => setShowSidebar(p => !p)}
        onToggleDashboard={() => setShowDashboard(p => !p)}
        onToggleSimBar={() => setShowSimBar(p => !p)}
        onFitViewport={() => window.dispatchEvent(new CustomEvent('tome:fit-viewport'))}
      />

      {/* Collapsible panels as overlays */}
      {showHeader && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, zIndex: 40,
          backdropFilter: 'blur(16px)', background: 'rgba(6, 10, 18, 0.88)',
        }}>
          <Header scanData={scanData} />
        </div>
      )}

      {showSidebar && (
        <div style={{
          position: 'absolute', top: showHeader ? 44 : 0, left: 0, bottom: 0, zIndex: 30,
          backdropFilter: 'blur(16px)', background: 'rgba(6, 10, 18, 0.88)',
          width: 280, borderRight: '1px solid var(--border)', overflowY: 'auto',
        }}>
          <Sidebar
            scanData={scanData}
            activeView="graph"
            setActiveView={() => {}}
            onSelectModule={handleSelectModule}
            selectedModule={selectedModule}
          />
        </div>
      )}

      {showDashboard && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 35,
          backdropFilter: 'blur(16px)', background: 'rgba(6, 10, 18, 0.94)',
          overflowY: 'auto',
        }}>
          <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 36 }}>
            <button
              onClick={() => setShowDashboard(false)}
              style={{
                width: 28, height: 28, borderRadius: 14,
                background: 'rgba(14, 20, 32, 0.85)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                fontSize: 14, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-mono)',
              }}
            >
              ×
            </button>
          </div>
          <Dashboard
            scanData={scanData}
            onSelectModule={(name) => {
              handleSelectModule(name);
              setShowDashboard(false);
            }}
          />
        </div>
      )}

      {showDetail && (selectedFile || selectedModule) && (
        <div style={{
          position: 'absolute', top: 0, right: 0, bottom: 0, zIndex: 30,
          backdropFilter: 'blur(16px)', background: 'rgba(6, 10, 18, 0.88)',
          animation: 'slide-in-right 200ms ease',
        }}>
          <DetailPanel
            scanData={scanData}
            selectedModule={selectedModule}
            selectedFile={selectedFile}
            onSelectModule={handleSelectModule}
            onSelectFile={handleSelectFile}
            onClose={() => { setSelectedFile(null); setSelectedModule(null); setShowDetail(false); }}
          />
        </div>
      )}

      {showSimBar && (
        <SimulationBar
          modules={scanData.modules}
          edges={moduleEdges}
          onSimulate={startSimulation}
          onClear={clearSimulation}
          simulationActive={!!simulationPath}
        />
      )}

      <FileDropZone onFileDrop={handleFileDrop} />
    </div>
  );
}
