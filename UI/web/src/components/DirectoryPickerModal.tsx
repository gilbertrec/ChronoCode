import React, { useEffect, useState } from 'react';
import { Folder, X } from 'lucide-react';

interface Directory {
  name: string;
  path: string;
}

interface DirectoryPickerModalProps {
  onSelect: (path: string) => void;
  onClose: () => void;
}

export const DirectoryPickerModal: React.FC<DirectoryPickerModalProps> = ({ onSelect, onClose }) => {
  const [currentPath, setCurrentPath] = useState('');
  const [directories, setDirectories] = useState<Directory[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDirectories = (path?: string) => {
    setLoading(true);
    const url = path ? `/api/directories?path=${encodeURIComponent(path)}` : '/api/directories';
    fetch(url)
      .then(res => res.json())
      .then(data => {
        setDirectories(data);
        if (data.length > 0 && data[0].name === '..') {
          // Find the parent to deduce current path roughly, but it's better if backend returns it
          // We'll just rely on what the user clicked if we don't have an exact endpoint returning the cwd.
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDirectories();
  }, []);

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
    fetchDirectories(path);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000
    }}>
      <div className="glass-card-dark" style={{ width: 500, maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Select Folder</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ marginBottom: 16, padding: 8, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 4 }}>
          <strong>Current:</strong> {currentPath || 'Home Directory'}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', marginBottom: 16, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4 }}>
          {loading ? (
            <div style={{ padding: 16, textAlign: 'center' }}>Loading...</div>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {directories.map((dir, idx) => (
                <li key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <button
                    onClick={() => handleNavigate(dir.path)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '12px 16px',
                      background: 'none', border: 'none', color: 'var(--text)',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12
                    }}
                    onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                    onMouseOut={e => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <Folder size={16} color="#818cf8" />
                    {dir.name}
                  </button>
                </li>
              ))}
              {directories.length === 0 && (
                <li style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)' }}>No subdirectories found.</li>
              )}
            </ul>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <button onClick={onClose} className="btn-primary" style={{ backgroundColor: 'transparent', border: '1px solid var(--text)' }}>
            Cancel
          </button>
          <button
            onClick={() => onSelect(currentPath)}
            className="btn-primary"
            disabled={!currentPath}
          >
            Select This Folder
          </button>
        </div>
      </div>
    </div>
  );
};
