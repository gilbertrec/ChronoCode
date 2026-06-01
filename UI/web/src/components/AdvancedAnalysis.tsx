import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { ResponsiveContainer, Treemap, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, LineChart, Line, PieChart, Pie, Cell } from 'recharts';

export const AdvancedAnalysis: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [timePeriod, setTimePeriod] = useState<'day' | 'week' | 'month'>('week');

  const [authorFilter, setAuthorFilter] = useState<'all' | 'ai' | 'human'>('all');

  useEffect(() => {
    setLoading(true);
    fetch(`/api/runs/${runId}/advanced_analysis?author_filter=${authorFilter}`)
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [runId, authorFilter]);

  if (loading) return <div>Loading advanced analysis...</div>;
  if (!data) return <div>Failed to load advanced analysis data.</div>;

  const { heatmap, temporal, categories } = data;

  // Format Treemap data
  const formatTreemap = (rawCounts: Record<string, number>) => {
    return Object.entries(rawCounts).map(([name, count]) => ({
      name,
      size: count
    })).filter(x => x.size > 0);
  };
  
  const introTreemapData = formatTreemap(heatmap.introduced_raw || {});
  const remTreemapData = formatTreemap(heatmap.removed_raw || {});

  // Format Lifecycle Data
  const lifecycleData = Object.entries(temporal.lifecycle || {}).map(([name, counts]: [string, any]) => ({
    name,
    Introduced: counts.introduced,
    Removed: counts.removed
  }));

  // Format Time Period Data
  const periodKey = `by_${timePeriod}`;
  const periodRaw = temporal[periodKey] || {};
  const periodData = Object.entries(periodRaw).map(([date, counts]: [string, any]) => ({
    date,
    Introduced: counts.introduced,
    Removed: counts.removed
  }));

  // Format Category Data
  const catData = Object.entries(categories || {}).map(([name, counts]: [string, any]) => ({
    name,
    Introduced: counts.introduced,
    Removed: counts.removed,
    Total: (counts.introduced || 0) + (counts.removed || 0)
  }));

  // Format AI vs Human Data
  const aiVsHuman = {
    AI: { introduced: 0, removed: 0 },
    Human: { introduced: 0, removed: 0 }
  };
  
  if (data.commit_log) {
    data.commit_log.forEach((commit: any) => {
      const tag = commit.tag === 'AI' ? 'AI' : 'Human';
      aiVsHuman[tag].introduced += commit.introduced || 0;
      aiVsHuman[tag].removed += commit.removed || 0;
    });
  }
  
  const aiHumanData = [
    { name: 'AI', Introduced: aiVsHuman.AI.introduced, Removed: aiVsHuman.AI.removed },
    { name: 'Human', Introduced: aiVsHuman.Human.introduced, Removed: aiVsHuman.Human.removed }
  ];

  const COLORS = ['#818cf8', '#34d399', '#f87171', '#fbbf24', '#a78bfa', '#60a5fa', '#f472b6'];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => navigate(-1)} className="btn-secondary" style={{ padding: 8 }}>
            <ArrowLeft size={20} />
          </button>
          <h2 style={{ margin: 0 }}>Advanced Data Analysis</h2>
        </div>

        <div style={{ display: 'flex', gap: 8, backgroundColor: 'var(--bg-card)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <button 
            className="btn-secondary"
            style={{ 
              backgroundColor: authorFilter === 'all' ? 'var(--primary)' : 'transparent', 
              color: authorFilter === 'all' ? '#fff' : 'var(--text-main)',
              border: 'none',
              boxShadow: authorFilter === 'all' ? 'var(--shadow-sm)' : 'none'
            }}
            onClick={() => setAuthorFilter('all')}
          >
            Both
          </button>
          <button 
            className="btn-secondary"
            style={{ 
              backgroundColor: authorFilter === 'human' ? 'var(--primary)' : 'transparent', 
              color: authorFilter === 'human' ? '#fff' : 'var(--text-main)',
              border: 'none',
              boxShadow: authorFilter === 'human' ? 'var(--shadow-sm)' : 'none'
            }}
            onClick={() => setAuthorFilter('human')}
          >
            Only Human
          </button>
          <button 
            className="btn-secondary"
            style={{ 
              backgroundColor: authorFilter === 'ai' ? 'var(--primary)' : 'transparent', 
              color: authorFilter === 'ai' ? '#fff' : 'var(--text-main)',
              border: 'none',
              boxShadow: authorFilter === 'ai' ? 'var(--shadow-sm)' : 'none'
            }}
            onClick={() => setAuthorFilter('ai')}
          >
            Only AI
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: 24, paddingBottom: 32 }}>
        
        {/* Treemap Introduced */}
        <div className="glass-card" style={{ height: 320, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: 16 }}>Smells Introduced (Treemap)</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            {introTreemapData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <Treemap data={introTreemapData} dataKey="size" stroke="#fff" fill="var(--primary)">
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                </Treemap>
              </ResponsiveContainer>
            ) : <p style={{ color: 'var(--text-muted)' }}>No smells introduced.</p>}
          </div>
        </div>

        {/* Treemap Removed */}
        <div className="glass-card" style={{ height: 320, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: 16 }}>Smells Removed (Treemap)</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            {remTreemapData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <Treemap data={remTreemapData} dataKey="size" stroke="#fff" fill="var(--success)">
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                </Treemap>
              </ResponsiveContainer>
            ) : <p style={{ color: 'var(--text-muted)' }}>No smells removed.</p>}
          </div>
        </div>

        {/* Lifecycle */}
        <div className="glass-card" style={{ height: 320, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: 16 }}>Project Lifecycle Distribution</h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={lifecycleData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} />
                <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                <Legend />
                <Bar dataKey="Introduced" fill="var(--danger)" />
                <Bar dataKey="Removed" fill="var(--success)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI vs Human Comparison */}
        <div className="glass-card" style={{ height: 320, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: 16 }}>AI vs Human Impact</h3>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {aiVsHuman.AI.introduced === 0 && aiVsHuman.AI.removed === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20 }}>
                <div style={{ fontSize: 40, marginBottom: 10 }}>🤖</div>
                <p style={{ margin: '0 0 8px 0', fontWeight: 500, color: 'var(--text-main)' }}>No AI Commits Detected</p>
                <p style={{ margin: 0, fontSize: '0.9em' }}>This comparison view is only available when AI-authored commits are present in the analysis.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={aiHumanData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                  <XAxis dataKey="name" stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} />
                  <YAxis stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                  <Legend wrapperStyle={{ paddingTop: '10px' }} />
                  <Bar dataKey="Introduced" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Removed" fill="var(--success)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Smell Evolution Over Time */}
        <div className="glass-card" style={{ height: 450, display: 'flex', flexDirection: 'column', gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>Smell Evolution Over Time</h3>
            <select 
              value={timePeriod} 
              onChange={e => setTimePeriod(e.target.value as any)}
              style={{ padding: '4px 8px' }}
            >
              <option value="day">Daily</option>
              <option value="week">Weekly</option>
              <option value="month">Monthly</option>
            </select>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            {periodData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={periodData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                  <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} angle={-45} textAnchor="end" height={60} />
                  <YAxis stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Line type="monotone" dataKey="Introduced" stroke="var(--primary)" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  <Line type="monotone" dataKey="Removed" stroke="var(--success)" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p style={{ color: 'var(--text-muted)' }}>No temporal data available.</p>}
          </div>
        </div>

        {/* Commit Category Distribution - span across all columns so it's wider */}
        <div className="glass-card" style={{ height: 350, display: 'flex', flexDirection: 'column', gridColumn: '1 / -1' }}>
          <h3 style={{ marginBottom: 16 }}>Commit Category Distribution (Total Smells Impacted)</h3>
          <div style={{ display: 'flex', flex: 1, minHeight: 0, justifyContent: 'center' }}>
            <ResponsiveContainer width="100%" height="100%" maxHeight={300}>
              <PieChart>
                <Pie data={catData} dataKey="Total" nameKey="name" cx="50%" cy="50%" innerRadius={70} outerRadius={100} label>
                  {catData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-main)', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
