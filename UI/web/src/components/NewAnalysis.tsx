import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, FolderSearch } from 'lucide-react';
import { DirectoryPickerModal } from './DirectoryPickerModal';

export const NewAnalysis: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    config_file: '',
    project_path: '',
    command_type: 'snapshot',
    commits: '',
    since: '',
    skip_tracker: false,
    workers: navigator.hardwareConcurrency ? String(navigator.hardwareConcurrency) : '4'
  });
  const [useConfig, setUseConfig] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [pickerTarget, setPickerTarget] = useState<'project_path' | 'config_file'>('project_path');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          useConfig
            ? { config_file: formData.config_file }
            : {
                ...formData,
                commits: formData.commits ? parseInt(formData.commits) : null,
                workers: formData.workers ? parseInt(formData.workers) : 1,
                config_file: null
              }
        )
      });
      
      if (res.ok) {
        alert('Analysis started in background. You can monitor the backend logs.');
        navigate('/');
      } else {
        alert('Failed to start analysis');
      }
    } catch (err) {
      console.error(err);
      alert('Error starting analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 700 }}>
      <h2>New Analysis</h2>
      
      <div className="glass-card" style={{ marginBottom: 16 }}>
        <div className="form-group checkbox-group" style={{ marginBottom: 0 }}>
          <input 
            type="checkbox" 
            id="useConfig"
            checked={useConfig}
            onChange={e => setUseConfig(e.target.checked)}
          />
          <label htmlFor="useConfig" style={{ margin: 0 }}>Use Configuration File instead of Manual Setup</label>
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="glass-card">
        {useConfig ? (
          <div className="form-group">
            <label>Config File Path (Absolute)</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input 
                type="text" 
                required 
                placeholder="/Users/.../default_config.yaml"
                value={formData.config_file}
                onChange={e => setFormData({...formData, config_file: e.target.value})}
                style={{ flex: 1 }}
              />
              <button 
                type="button" 
                className="btn-primary" 
                onClick={() => { setPickerTarget('config_file'); setShowPicker(true); }}
                style={{ padding: '8px 12px' }}
                title="Choose folder containing config file"
              >
                <FolderSearch size={18} />
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="form-group">
              <label>Command Type</label>
              <select 
                value={formData.command_type} 
                onChange={e => setFormData({...formData, command_type: e.target.value})}
              >
                <option value="snapshot">Snapshot (Latest Commit vs Parent)</option>
                <option value="history">History (Walk commit history)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Project Path (Absolute)</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input 
                  type="text" 
                  required 
                  placeholder="/Users/.../MyProject"
                  value={formData.project_path}
                  onChange={e => setFormData({...formData, project_path: e.target.value})}
                  style={{ flex: 1 }}
                />
                <button 
                  type="button" 
                  className="btn-primary" 
                  onClick={() => { setPickerTarget('project_path'); setShowPicker(true); }}
                  style={{ padding: '8px 12px' }}
                >
                  <FolderSearch size={18} />
                </button>
              </div>
            </div>

            {formData.command_type === 'history' && (
              <>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Max Commits</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 50"
                      value={formData.commits}
                      onChange={e => setFormData({...formData, commits: e.target.value})}
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Since Date</label>
                    <input 
                      type="text" 
                      placeholder="e.g. 2023-01-01"
                      value={formData.since}
                      onChange={e => setFormData({...formData, since: e.target.value})}
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Parallel Workers (Threads)</label>
                  <input 
                    type="number" 
                    min="1"
                    placeholder="e.g. 4"
                    value={formData.workers}
                    onChange={e => setFormData({...formData, workers: e.target.value})}
                  />
                  <small style={{ color: 'var(--text-muted)' }}>Default is based on your machine's logical cores.</small>
                </div>
                
                <div className="form-group checkbox-group">
                  <input 
                    type="checkbox" 
                    id="skipTracker"
                    checked={formData.skip_tracker}
                    onChange={e => setFormData({...formData, skip_tracker: e.target.checked})}
                  />
                  <label htmlFor="skipTracker" style={{ margin: 0 }}>Skip StaticTracker (Faster, less accurate)</label>
                </div>
              </>
            )}
          </>
        )}

        <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: 16 }}>
          <Play size={18} /> {loading ? 'Starting...' : 'Run Analysis'}
        </button>
      </form>

      {showPicker && (
        <DirectoryPickerModal 
          onSelect={path => {
            if (pickerTarget === 'project_path') {
              setFormData({ ...formData, project_path: path });
            } else {
              // Usually config files are files, but we can set the dir path and let them add /config.yaml manually
              setFormData({ ...formData, config_file: path + '/default_config.yaml' });
            }
            setShowPicker(false);
          }}
          onClose={() => setShowPicker(false)}
        />
      )}
    </div>
  );
};
