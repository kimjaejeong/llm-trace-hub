import ProjectTabs from "../../../components/project-tabs";

export default async function ProjectLayout({ children, params }) {
  const { projectId } = await params;

  return (
    <div className="grid" style={{ gap: 12 }}>
      <ProjectTabs projectId={projectId} />
      {children}
    </div>
  );
}
