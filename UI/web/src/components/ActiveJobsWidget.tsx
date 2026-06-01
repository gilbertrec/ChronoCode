import React, { useEffect, useState } from 'react';
import { XCircle, Loader2 } from 'lucide-react';

interface Job {
  id: string;
  project: string;
  type: string;
  progress_current: number;
  progress_total: number;
  status: string;
}

export const ActiveJobsWidget: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch('/api/jobs');
        if (res.ok) {
          const data = await res.json();
          setJobs(data);
        }
      } catch (err) {
        console.error("Failed to fetch jobs", err);
      }
    };

    fetchJobs();
    const interval = setInterval(fetchJobs, 2000); // poll every 2s
    return () => clearInterval(interval);
  }, []);

  const handleStop = async (jobId: string) => {
    try {
      await fetch(`/api/jobs/${jobId}/stop`, { method: 'POST' });
      // Optimistically remove from state
      setJobs(jobs.filter(j => j.id !== jobId));
    } catch (err) {
      console.error("Failed to stop job", err);
    }
  };

  if (jobs.length === 0) return null;

  return (
    <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h4 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Active Processes
      </h4>
      {jobs.map(job => {
        const label = `${job.type.charAt(0).toUpperCase() + job.type.slice(1)} process running on ${job.project}`;
        const isHistory = job.type === 'history';
        const progressPercent = isHistory && job.progress_total > 0 
          ? Math.round((job.progress_current / job.progress_total) * 100) 
          : null;

        return (
          <div key={job.id} style={{
            backgroundColor: 'var(--bg-card)',
            padding: '12px',
            borderRadius: '8px',
            boxShadow: 'var(--shadow-sm)',
            border: '1px solid var(--border-color)',
            position: 'relative'
          }}>
            <button 
              onClick={() => handleStop(job.id)}
              style={{
                position: 'absolute',
                top: '8px',
                right: '8px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                padding: '4px'
              }}
              title="Stop process"
            >
              <XCircle size={16} />
            </button>

            <div style={{ paddingRight: '24px', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.4 }}>
              {label}
            </div>

            {isHistory && progressPercent !== null ? (
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  <span>{job.progress_current} / {job.progress_total}</span>
                  <span>{progressPercent}%</span>
                </div>
                <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-main)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${progressPercent}%`, height: '100%', backgroundColor: 'var(--primary)', transition: 'width 0.3s ease' }} />
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--primary)' }}>
                <Loader2 size={14} className="spin" /> Processing...
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
