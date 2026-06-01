import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, CheckCircle, XCircle } from 'lucide-react';

interface RunManifest {
  run_id: string;
  project: string;
  mode: string;
  child_commit: string;
  parent_commit: string;
  changed_py_files: number;
  dpy_smells_before: number;
  dpy_smells_after: number;
  tracker_success: boolean;
  introduced: number;
  removed: number;
}

export const SnapshotDashboard: React.FC = () => {
  const [runs, setRuns] = useState<RunManifest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRuns = () => {
      fetch('/api/runs')
        .then(res => res.json())
        .then(data => {
          // Filter out history runs
          const snapshotRuns = data.filter((r: any) => r.mode !== 'history');
          setRuns(snapshotRuns);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    };

    fetchRuns();
    const interval = setInterval(fetchRuns, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading snapshot runs...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2>Snapshot Analyses</h2>
        <Link to="/new" className="btn-primary">
          <Play size={18} /> Run New Analysis
        </Link>
      </div>

      {runs.length === 0 ? (
        <div className="glass-card">No snapshot runs found in DataStore.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {runs.map(run => (
            <Link key={run.run_id} to={`/runs/${run.run_id}`} className="glass-card interactive" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'inherit' }}>
              <div>
                <h3 style={{ marginBottom: 8, fontSize: '1.2rem' }}>{run.project}</h3>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', gap: 16 }}>
                  <span>Run ID: {run.run_id.split('_').pop()}</span>
                  <span>Commit: {run.child_commit ? run.child_commit.substring(0, 8) : 'unknown'}</span>
                  <span>Files Changed: {run.changed_py_files}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--danger)' }}>+{run.introduced}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Introduced</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>-{run.removed}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Removed</div>
                </div>
                <div>
                  {run.tracker_success ? <CheckCircle color="var(--success)" /> : <XCircle color="var(--danger)" />}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
