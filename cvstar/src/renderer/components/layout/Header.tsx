import React from 'react';
import './Header.css';

const Header: React.FC = () => {
  return (
    <header className="header">
      <h1 className="header-title">Your Projects</h1>
      <div className="header-controls">
        <input type="text" className="search-bar" placeholder="Search projects..." />
        <div className="view-controls">
          <button className="view-btn list-view active">List</button>
          <button className="view-btn grid-view">Grid</button>
        </div>
        <div className="import-dropdown">
          <button className="import-btn">Import ▼</button>
          <div className="import-menu">
            <div className="import-item">From URL</div>
            <div className="import-item">Paste Description</div>
            <div className="import-item">Email Forward</div>
          </div>
        </div>
        <button className="new-project-btn">+ New</button>
      </div>
    </header>
  );
};

export default Header;