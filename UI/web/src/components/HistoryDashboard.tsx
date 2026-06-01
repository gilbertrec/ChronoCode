import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play } from 'lucide-react';

export const HistoryDashboard: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRuns = () => {
      fetch('/api/runs')
        .then(res => res.json())
        .then(data => {
          const historyRuns = data.filter((r: any) => r.mode === 'history');
          setRuns(historyRuns);
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

  if (loading) return <div>Loading history runs...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2>History Analyses</h2>
        <Link to="/new" className="btn-primary">
          <Play size={18} /> Run New Analysis
        </Link>
      </div>

      {runs.length === 0 ? (
        <div className="glass-card">No history runs found in DataStore.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {runs.map(run => {
            const human = run.aggregated?.Human || { introduced: 0, removed: 0 };
            const ai = run.aggregated?.AI || { introduced: 0, removed: 0 };
            const totalIntroduced = human.introduced + ai.introduced;
            const totalRemoved = human.removed + ai.removed;

            return (
              <Link key={run.run_id} to={`/runs/${run.run_id}`} className="glass-card interactive" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'inherit' }}>
                <div>
                  <h3 style={{ marginBottom: 8, fontSize: '1.2rem' }}>{run.project}</h3>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', gap: 16 }}>
                    <span>Run ID: {run.run_id.split('_').pop()}</span>
                    <span>Commits Analyzed: {run.commits_analysed} / {run.total_commits_inspected}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--danger)' }}>+{totalIntroduced}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Introduced</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>-{totalRemoved}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Removed</div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
};
