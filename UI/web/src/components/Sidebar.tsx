import React from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, History, PlusCircle, Settings } from 'lucide-react';
import { ActiveJobsWidget } from './ActiveJobsWidget';
import logo from '../assets/chrono_code_no_bg.png';

export const Sidebar: React.FC = () => {
  return (
    <div className="sidebar">
      <h1>
        <img src={logo} alt="ChronoCode Logo" style={{ width: 200, height: 200, objectFit: 'contain' }} />
      </h1>
      <nav className="nav-links">
        {/* <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Activity size={20} />
          Snapshot Runs
        </NavLink> */}
        <NavLink to="/history-runs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <History size={20} />
          History Runs
        </NavLink>
        <NavLink to="/new" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <PlusCircle size={20} />
          New Analysis
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Settings size={20} />
          Settings
        </NavLink>
      </nav>
      <ActiveJobsWidget />
    </div>
  );
};
