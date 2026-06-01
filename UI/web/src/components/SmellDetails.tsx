import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export const SmellDetails: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { smell, commitSha, type } = location.state || {};
  const [diff, setDiff] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!smell || !commitSha) {
      setLoading(false);
      return;
    }
    const filePath = smell.File || smell['source path'] || smell.file || '';
    fetch(`/api/runs/${runId}/diff?commit_sha=${commitSha}&file_path=${encodeURIComponent(filePath)}`)
      .then(r => r.json())
      .then(data => {
        setDiff(data.diff || 'No diff found.');
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setDiff('Failed to load diff.');
        setLoading(false);
      });
  }, [runId, commitSha, smell]);

  if (!smell) return <div>No smell data provided. Go back and select a smell from the commit breakdown.</div>;

  const lineStr = smell.Line || smell.line || smell.start || '0';
  const targetLine = parseInt(String(lineStr).split('-')[0], 10);

  const parsedDiff = React.useMemo(() => {
    if (!diff || diff === 'No diff found.' || diff.startsWith('Failed')) return [];
    
    const lines = diff.split('\n');
    let oldLineNum = 0;
    let newLineNum = 0;
    const parsed: any[] = [];
    let inHunk = false;

    for (const line of lines) {
      if (line.startsWith('@@ ')) {
        inHunk = true;
        const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
        if (match) {
          oldLineNum = parseInt(match[1], 10);
          newLineNum = parseInt(match[2], 10);
        }
        continue;
      }
      
      if (!inHunk) continue;
      
      if (line.startsWith('-')) {
        parsed.push({ type: 'removed', content: line, oldL: oldLineNum++, newL: '' });
      } else if (line.startsWith('+')) {
        parsed.push({ type: 'added', content: line, oldL: '', newL: newLineNum++ });
      } else if (line.startsWith(' ')) {
        parsed.push({ type: 'context', content: line, oldL: oldLineNum++, newL: newLineNum++ });
      }
    }

    if (!targetLine) return parsed;

    const minLine = targetLine - 15;
    const maxLine = targetLine + 15;

    return parsed.filter(p => {
      const o = typeof p.oldL === 'number' ? p.oldL : -1;
      const n = typeof p.newL === 'number' ? p.newL : -1;
      return (o >= minLine && o <= maxLine) || (n >= minLine && n <= maxLine);
    });
  }, [diff, targetLine]);

  const renderParsedLine = (p: any, idx: number) => {
    let color = '#e2e8f0';
    let bg = 'transparent';
    let isTarget = false;
    
    if (p.type === 'added') {
      color = '#34d399';
      bg = 'rgba(16, 185, 129, 0.15)';
    } else if (p.type === 'removed') {
      color = '#f87171';
      bg = 'rgba(239, 68, 68, 0.15)';
    }
    
    // highlight the target line where the smell is located
    if (p.oldL === targetLine || p.newL === targetLine) {
       bg = 'rgba(129, 140, 248, 0.3)';
       isTarget = true;
    }

    return (
      <div key={idx} style={{ display: 'flex', backgroundColor: bg, color, fontFamily: 'monospace', fontSize: '0.9rem' }}>
        <div style={{ width: 45, textAlign: 'right', padding: '2px 8px', color: '#64748b', userSelect: 'none', borderRight: '1px solid #334155' }}>
          {p.oldL}
        </div>
        <div style={{ width: 45, textAlign: 'right', padding: '2px 8px', color: '#64748b', userSelect: 'none', borderRight: '1px solid #334155' }}>
          {p.newL}
        </div>
        <div style={{ padding: '2px 16px', whiteSpace: 'pre-wrap', flex: 1, position: 'relative' }}>
          {isTarget && <div style={{ position: 'absolute', left: 4, top: 2, color: '#818cf8' }}>▶</div>}
          {p.content}
        </div>
      </div>
    );
  };

  const name = smell.Bug || smell.smell_name || smell['SmellName'] || smell.smell || smell['class name'] || 'Unknown Smell';
  const category = smell.smell_type || smell.category || 'N/A';
  const method = smell.Method || smell['method name'] || '';
  const file = smell.File || smell['source path'] || smell.file || '';
  const line = smell.Line || smell.line || smell.start || '';
  const description = smell.Description || smell.cause || smell.description || '';

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(-1)} className="btn-secondary" style={{ padding: 8 }}>
          <ArrowLeft size={20} />
        </button>
        <h2>Smell Details</h2>
        <span className={`badge ${type === 'introduced' ? 'danger' : 'success'}`}>
          {type === 'introduced' ? 'Introduced' : 'Removed'} in {commitSha?.substring(0,8)}
        </span>
      </div>

      <div className="glass-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>{name}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div><strong>Category:</strong> {category}</div>
          <div><strong>File:</strong> <span style={{fontFamily: 'monospace'}}>{file}</span></div>
          <div><strong>Method/Class:</strong> <span style={{fontFamily: 'monospace'}}>{method || 'N/A'}</span></div>
          <div><strong>Line:</strong> {line}</div>
        </div>
        <div>
          <strong>Description:</strong>
          <p style={{ marginTop: 8, color: 'var(--text-muted)' }}>{description}</p>
        </div>
      </div>

      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)', backgroundColor: 'rgba(0,0,0,0.02)' }}>
          <h3 style={{ margin: 0 }}>Git Diff Context (±15 Lines)</h3>
        </div>
        <div style={{ padding: '16px 0', backgroundColor: '#1e1e2d', color: '#e2e8f0', overflowX: 'auto', maxHeight: '600px', overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: '0 24px' }}>Loading diff...</div>
          ) : parsedDiff.length > 0 ? (
            parsedDiff.map(renderParsedLine)
          ) : (
            <div style={{ padding: '0 24px', color: '#64748b' }}>
              Diff unavailable or line {targetLine} was not modified in this commit.
              <br/>Raw diff fallback:
              <pre style={{ marginTop: 16 }}>{diff}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
