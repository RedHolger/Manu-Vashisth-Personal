import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import ProjectsListPage from '../../pages/ProjectsListPage';
import './MainLayout.css';

const MainLayout: React.FC = () => {
  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <Header />
        <ProjectsListPage />
      </div>
    </div>
  );
};

export default MainLayout;