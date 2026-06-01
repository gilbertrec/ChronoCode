import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, X, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const RunDetails: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [manifest, setManifest] = useState<any>(null);
  const [smells, setSmells] = useState<{introduced: any[], removed: any[]}>({ introduced: [], removed: [] });
  const [historyLog, setHistoryLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'introduced' | 'removed'>('introduced');

  // Modal for History commit details
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);
  const [commitSmells, setCommitSmells] = useState<{introduced: any[], removed: any[]}>({ introduced: [], removed: [] });
  const [loadingCommit, setLoadingCommit] = useState(false);

  useEffect(() => {
    fetch(`/api/runs/${runId}`)
      .then(r => r.json())
      .then(manifestData => {
        setManifest(manifestData);
        if (manifestData.mode === 'history') {
          return fetch(`/api/runs/${runId}/history`)
            .then(r => r.json())
            .then(log => {
              // Filter out commits that introduced and removed 0 smells
              const relevantLog = log.filter((l: any) => l.introduced > 0 || l.removed > 0);
              // Reverse log so oldest is first for the chart
              setHistoryLog([...relevantLog].reverse());
              setLoading(false);
            });
        } else {
          return fetch(`/api/runs/${runId}/smells`)
            .then(r => r.json())
            .then(smellsData => {
              setSmells(smellsData);
              setLoading(false);
            });
        }
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [runId]);

  const loadCommitSmells = (sha: string) => {
    setSelectedCommit(sha);
    setLoadingCommit(true);
    fetch(`/api/runs/${runId}/history/smells?commit_sha=${sha}`)
      .then(r => r.json())
      .then(data => {
        setCommitSmells(data);
        setActiveTab('introduced');
        setLoadingCommit(false);
      })
      .catch(e => {
        console.error(e);
        setLoadingCommit(false);
      });
  };

  if (loading) return <div>Loading details...</div>;
  if (!manifest) return <div>Run not found</div>;

  const currentSmells = activeTab === 'introduced' ? (selectedCommit ? commitSmells.introduced : smells.introduced) : (selectedCommit ? commitSmells.removed : smells.removed);

  const renderSmellsTable = () => (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Name</th>
            <th>File</th>
            <th>Method</th>
            <th>Line</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {currentSmells.map((s, idx) => (
            <tr 
              key={idx}
              onClick={() => navigate(`/runs/${runId}/smell`, { state: { smell: s, commitSha: selectedCommit || manifest?.child_commit, type: activeTab } })}
              style={{ cursor: 'pointer', transition: 'background 0.2s' }}
              onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.02)'}
              onMouseOut={e => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <td><span className="badge">{s.smell_type || s.category}</span></td>
              <td>{s.Bug || s.smell_name || s['SmellName'] || s.smell || s['class name']}</td>
              <td><span style={{fontFamily: 'monospace'}}>{s.File || s['source path'] || s.file}</span></td>
              <td><span style={{fontFamily: 'monospace'}}>{s.Method || s['method name']}</span></td>
              <td>{s.Line || s.line || s.start}</td>
              <td style={{ maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.Description || s.cause || s.description}
              </td>
            </tr>
          ))}
          {currentSmells.length === 0 && (
            <tr>
              <td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                No smells found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => navigate(-1)} className="btn-secondary" style={{ padding: 8 }}>
            <ArrowLeft size={20} />
          </button>
          <h2>Run Details: {manifest.project} <span style={{fontSize: '1rem', color: 'var(--text-muted)'}}>({manifest.mode})</span></h2>
        </div>
        {manifest.mode === 'history' && (
          <Link to={`/runs/${runId}/advanced`} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={18} /> Advanced Data Analysis
          </Link>
        )}
      </div>
      
      {manifest.mode === 'history' ? (
        <>
          <div className="glass-card" style={{ marginBottom: 32, height: 400 }}>
            <h3 style={{ marginBottom: 16 }}>Smells Introduced / Removed Over Time</h3>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyLog} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="sha" tickFormatter={sha => sha.substring(0,6)} stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }}
                  labelFormatter={label => `Commit: ${label.substring(0,8)}`}
                />
                <Legend />
                <Line type="monotone" dataKey="introduced" stroke="var(--danger)" strokeWidth={2} name="Introduced" activeDot={{ r: 8 }} />
                <Line type="monotone" dataKey="removed" stroke="var(--success)" strokeWidth={2} name="Removed" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <h3>Commit Breakdown</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Click a row to view specific smells introduced/removed in that commit.</p>
          <div className="table-container" style={{ marginBottom: 40 }}>
            <table>
              <thead>
                <tr>
                  <th>Commit</th>
                  <th>Message</th>
                  <th>Author</th>
                  <th>Co-Authors</th>
                  <th>Files</th>
                  <th style={{ color: 'var(--danger)' }}>Introduced</th>
                  <th style={{ color: 'var(--success)' }}>Removed</th>
                </tr>
              </thead>
              <tbody>
                {historyLog.map((log, idx) => (
                  <tr 
                    key={idx} 
                    onClick={() => loadCommitSmells(log.sha)}
                    style={{ cursor: 'pointer', transition: 'background 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
                    onMouseOut={e => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <td style={{ fontFamily: 'monospace' }}>{log.sha.substring(0,8)}</td>
                    <td style={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{log.subject}</td>
                    <td>{log.author_name}</td>
                    <td>
                      {log.co_authors && log.co_authors.length > 0 ? (
                        <div style={{ fontSize: '0.8rem' }}>
                          {log.co_authors.map((ca: string, i: number) => <div key={i}>{ca}</div>)}
                        </div>
                      ) : '-'}
                    </td>
                    <td>{log.changed_py_files}</td>
                    <td style={{ fontWeight: 'bold', color: log.introduced > 0 ? 'var(--danger)' : 'inherit' }}>{log.introduced}</td>
                    <td style={{ fontWeight: 'bold', color: log.removed > 0 ? 'var(--success)' : 'inherit' }}>{log.removed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedCommit && (
            <div style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: 'rgba(255,255,255,0.4)', backdropFilter: 'blur(4px)', zIndex: 1000,
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <div className="glass-card" style={{ width: '90%', maxWidth: 1000, maxHeight: '90vh', display: 'flex', flexDirection: 'column', backgroundColor: '#ffffff', boxShadow: '0 10px 30px rgba(0,0,0,0.1)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                  <h3>Commit: {selectedCommit.substring(0,8)}</h3>
                  <button onClick={() => setSelectedCommit(null)} style={{ background: 'none', border: 'none', color: 'var(--text)', cursor: 'pointer' }}>
                    <X size={24} />
                  </button>
                </div>
                
                {loadingCommit ? (
                  <div style={{ padding: 40, textAlign: 'center' }}>Loading smells for this commit...</div>
                ) : (
                  <>
                    <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
                      <button 
                        onClick={() => setActiveTab('introduced')}
                        className={`glass-card ${activeTab === 'introduced' ? '' : 'interactive'}`}
                        style={{ flex: 1, textAlign: 'center', borderColor: activeTab === 'introduced' ? 'var(--primary)' : '' }}
                      >
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--danger)' }}>+{commitSmells.introduced.length}</div>
                        <div>Introduced</div>
                      </button>
                      <button 
                        onClick={() => setActiveTab('removed')}
                        className={`glass-card ${activeTab === 'removed' ? '' : 'interactive'}`}
                        style={{ flex: 1, textAlign: 'center', borderColor: activeTab === 'removed' ? 'var(--primary)' : '' }}
                      >
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>-{commitSmells.removed.length}</div>
                        <div>Removed</div>
                      </button>
                    </div>
                    
                    <div style={{ flex: 1, overflowY: 'auto' }}>
                      {renderSmellsTable()}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="glass-card" style={{ marginBottom: 32, display: 'flex', gap: 48 }}>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Commit Range</div>
              <div style={{ fontFamily: 'monospace' }}>{manifest.parent_commit.substring(0,8)} → {manifest.child_commit.substring(0,8)}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Files Changed</div>
              <div>{manifest.changed_py_files}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Total Smells Before / After</div>
              <div>{manifest.dpy_smells_before} / {manifest.dpy_smells_after}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <button 
              onClick={() => setActiveTab('introduced')}
              className={`glass-card ${activeTab === 'introduced' ? '' : 'interactive'}`}
              style={{ flex: 1, textAlign: 'center', borderColor: activeTab === 'introduced' ? 'var(--primary)' : '' }}
            >
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--danger)' }}>+{manifest.introduced}</div>
              <div>Introduced Smells</div>
            </button>
            <button 
              onClick={() => setActiveTab('removed')}
              className={`glass-card ${activeTab === 'removed' ? '' : 'interactive'}`}
              style={{ flex: 1, textAlign: 'center', borderColor: activeTab === 'removed' ? 'var(--primary)' : '' }}
            >
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--success)' }}>-{manifest.removed}</div>
              <div>Removed Smells</div>
            </button>
          </div>

          {renderSmellsTable()}
        </>
      )}
    </div>
  );
};
