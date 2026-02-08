import Link from "next/link";
import { fetchApi } from "../../components/api";
import ProjectCreateForm from "../../components/project-create-form";
import ProjectAdminActions from "../../components/project-admin-actions";

export default async function ProjectsPage() {
  let projects = [];
  let loadError = null;
  try {
    projects = await fetchApi("/api/v1/projects", { useAdmin: true });
  } catch (err) {
    loadError = err?.message || "failed to load projects";
  }

  return (
    <div className="grid">
      {loadError ? (
        <div className="card alert-card">
          <h3 className="subhead">Project Load Error</h3>
          <p className="subtitle">{loadError}</p>
        </div>
      ) : null}

      <div className="card">
        <h1 className="title">Projects</h1>
        <p className="subtitle">프로젝트(에이전트) 단위로 Trace Dashboard와 Cases를 분리 관리합니다.</p>
      </div>

      <ProjectCreateForm />

      <div className="card">
        <h3 className="subhead">Project List</h3>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead>
              <tr><th>Project</th><th>Status</th><th>Trace Count</th><th>Open Cases</th><th>Created</th><th>Open</th><th>Admin</th></tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td><span className={p.is_active ? "pill ok" : "pill neutral"}>{p.is_active ? "active" : "inactive"}</span></td>
                  <td>{p.trace_count}</td>
                  <td>{p.open_case_count}</td>
                  <td>{new Date(p.created_at).toLocaleString()}</td>
                  <td style={{ display: "flex", gap: 8 }}>
                    {p.is_active ? (
                      <>
                        <Link className="button detail-btn" href={`/?project_id=${p.id}`}>Dashboard</Link>
                        <Link className="button detail-btn" href={`/cases?project_id=${p.id}`}>Cases</Link>
                      </>
                    ) : (
                      <span className="subtitle">Activate 후 접근 가능</span>
                    )}
                  </td>
                  <td><ProjectAdminActions projectId={p.id} isActive={p.is_active} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
