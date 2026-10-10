import React from 'react';

interface Project {
  id: number;
  name: string;
  created: string;
}

interface ProjectCardProps {
  project: Project;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project }) => {
  return (
    <div className="project-card">
      <div className="project-info">
        <h3 className="project-name">{project.name}</h3>
        <p className="project-date">Created: {project.created}</p>
      </div>
      <div className="project-actions">
        <button className="open-btn">Open</button>
        <button className="menu-btn">⋮</button>
      </div>
    </div>
  );
};

export default ProjectCard;
