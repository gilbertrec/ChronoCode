import React, { useEffect, useState } from 'react';
import { Save } from 'lucide-react';

export const Settings: React.FC = () => {
  const [formData, setFormData] = useState({
    dpy_path: '',
    python: '',
    java_home: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/settings')
      .then(res => res.json())
      .then(data => {
        setFormData({
          dpy_path: data['dpy-path'] || '',
          python: data['python'] || '',
          java_home: data['java-home'] || ''
        });
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        alert('Settings saved successfully!');
      } else {
        alert('Failed to save settings');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading settings...</div>;

  return (
    <div style={{ maxWidth: 600 }}>
      <h2>Global Settings</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        These settings are saved to <code>settings.yaml</code> and will be used as the default for all new analyses.
      </p>
      
      <form onSubmit={handleSubmit} className="glass-card">
        <div className="form-group">
          <label>DesignitePy (DPy) Path (Absolute)</label>
          <input 
            type="text" 
            placeholder="/Users/.../DesignitePy"
            value={formData.dpy_path}
            onChange={e => setFormData({...formData, dpy_path: e.target.value})}
          />
        </div>

        <div className="form-group">
          <label>Python Executable Override</label>
          <input 
            type="text" 
            placeholder="arch -x86_64 /path/to/.venv_x86/bin/python"
            value={formData.python}
            onChange={e => setFormData({...formData, python: e.target.value})}
          />
          <small style={{ color: 'var(--text-muted)' }}>
            Leave blank to use the default environment.
          </small>
        </div>

        <div className="form-group" style={{ marginBottom: 24 }}>
          <label>JAVA_HOME Override</label>
          <input 
            type="text" 
            placeholder="/Library/Java/JavaVirtualMachines/openjdk-19.0.1/Contents/Home"
            value={formData.java_home}
            onChange={e => setFormData({...formData, java_home: e.target.value})}
          />
          <small style={{ color: 'var(--text-muted)' }}>
            Leave blank to use the system JAVA_HOME.
          </small>
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          <Save size={18} /> {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
};
