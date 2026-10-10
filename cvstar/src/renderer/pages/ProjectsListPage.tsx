import React from 'react';
import ProjectCard from '../components/ProjectCard';
import './ProjectsListPage.css';

const ProjectsListPage: React.FC = () => {
  // Sample project data - would come from state/storage in real implementation
  const projects = [
    { id: 1, name: 'Software Engineer Resume', created: '2026-03-20' },
    { id: 2, name: 'Data Scientist CV', created: '2026-03-15' },
    { id: 3, name: 'Product Manager Profile', created: '2026-03-10' }
  ];

  return (
    <main className="projects-list-page">
      <div className="projects-table">
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </main>
  );
};

export default ProjectsListPage;