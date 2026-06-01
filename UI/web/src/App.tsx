
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { SnapshotDashboard } from './components/SnapshotDashboard';
import { HistoryDashboard } from './components/HistoryDashboard';
import { RunDetails } from './components/RunDetails';
import { AdvancedAnalysis } from './components/AdvancedAnalysis';
import { NewAnalysis } from './components/NewAnalysis';
import { SmellDetails } from './components/SmellDetails';
import { Settings } from './components/Settings';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            {/* <Route path="/" element={<SnapshotDashboard />} /> */}
            <Route path="/" element={<Navigate to="/history-runs" replace />} />
            <Route path="/history-runs" element={<HistoryDashboard />} />
            <Route path="/new" element={<NewAnalysis />} />
            <Route path="/runs/:runId" element={<RunDetails />} />
            <Route path="/runs/:runId/smell" element={<SmellDetails />} />
            <Route path="/runs/:runId/advanced" element={<AdvancedAnalysis />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
