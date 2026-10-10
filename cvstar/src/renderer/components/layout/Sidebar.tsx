import React from 'react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        <div className="nav-item active">All Projects</div>
        <div className="nav-item">Your Projects</div>
        <div className="nav-item">Shared with you</div>
      </nav>
    </aside>
  );
};

export default Sidebar;