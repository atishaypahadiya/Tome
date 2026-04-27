import { useState, useCallback, useEffect } from 'react';

export default function FileDropZone({ onFileDrop }) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const jsonFile = files.find(f => f.name.endsWith('.json'));
    if (!jsonFile) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target.result);
        onFileDrop(data);
      } catch {
        console.error('Failed to parse JSON file');
      }
    };
    reader.readAsText(jsonFile);
  }, [onFileDrop]);

  useEffect(() => {
    const handleWindowDragOver = (e) => {
      e.preventDefault();
      setIsDragging(true);
    };
    const handleWindowDragLeave = (e) => {
      if (e.relatedTarget === null) {
        setIsDragging(false);
      }
    };
    const handleWindowDrop = (e) => {
      e.preventDefault();
      setIsDragging(false);
    };

    window.addEventListener('dragover', handleWindowDragOver);
    window.addEventListener('dragleave', handleWindowDragLeave);
    window.addEventListener('drop', handleWindowDrop);

    return () => {
      window.removeEventListener('dragover', handleWindowDragOver);
      window.removeEventListener('dragleave', handleWindowDragLeave);
      window.removeEventListener('drop', handleWindowDrop);
    };
  }, []);

  if (!isDragging) return null;

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(10, 10, 15, 0.92)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div style={{
        border: '2px dashed var(--border)',
        borderRadius: 16,
        padding: '60px 80px',
        textAlign: 'center',
        pointerEvents: 'none',
      }}>
        <div style={{
          fontSize: 14,
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          marginBottom: 8,
        }}>
          Drop Tome JSON file
        </div>
        <div style={{
          fontSize: 10,
          color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)',
        }}>
          .json
        </div>
      </div>
    </div>
  );
}
