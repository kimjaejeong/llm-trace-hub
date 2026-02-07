import Link from "next/link";
import { fetchApi } from "../components/api";

function pill(status) {
  if (status === "success") return "pill ok";
  if (status === "error") return "pill err";
  return "pill warn";
}

function decisionPill(action) {
  if (!action) return <span className="pill neutral">none</span>;
  if (action === "ALLOW_ANSWER") return <span className="pill ok">{action}</span>;
  if (action === "ESCALATE" || action === "BLOCK") return <span className="pill err">{action}</span>;
  return <span className="pill warn">{action}</span>;
}

export default async function TracesPage({ searchParams }) {
  const params = await searchParams;
  const q = new URLSearchParams(params || {});
  q.set("page", q.get("page") || "1");
  q.set("page_size", q.get("page_size") || "20");

  const [data, stats] = await Promise.all([
    fetchApi(`/api/v1/traces?${q.toString()}`),
    fetchApi("/api/v1/traces/stats/overview?last_hours=24"),
  ]);

  return (
    <div className="grid">
      <div className="card">
        <h1 className="title">LLM Observability Dashboard</h1>
        <p className="subtitle">LangGraph node tracing, decision outcomes, and trace health in one place.</p>

        <div className="stats-grid">
          <div className="stat"><div className="label">Open Traces</div><div className="value">{stats.totals.open_traces}</div></div>
          <div className="stat"><div className="label">Success Traces</div><div className="value">{stats.totals.success_traces}</div></div>
          <div className="stat"><div className="label">Error Traces</div><div className="value">{stats.totals.error_traces}</div></div>
          <div className="stat"><div className="label">LangGraph Nodes</div><div className="value">{stats.span_types.langgraph_node || 0}</div></div>
          <div className="stat"><div className="label">Escalations</div><div className="value">{stats.decisions.ESCALATE || 0}</div></div>
        </div>
      </div>

      <div className="card">
        <form className="filters" method="get">
          <input className="input" name="status" placeholder="status" defaultValue={params?.status || ""} />
          <input className="input" name="model" placeholder="model" defaultValue={params?.model || ""} />
          <input className="input" name="environment" placeholder="environment" defaultValue={params?.environment || ""} />
          <input className="input" name="user_id" placeholder="user_id" defaultValue={params?.user_id || ""} />
          <input className="input" name="session_id" placeholder="session_id" defaultValue={params?.session_id || ""} />
          <input className="input" name="search" placeholder="input/output/logs search" defaultValue={params?.search || ""} />
          <button className="button" type="submit">Apply Filters</button>
        </form>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Trace</th>
                <th>Status</th>
                <th>Model</th>
                <th>Env</th>
                <th>User/Session</th>
                <th>Completion</th>
                <th>Decision</th>
                <th>Review</th>
                <th>LangGraph</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id}>
                  <td><Link href={`/traces/${row.id}`}>{row.id}</Link></td>
                  <td><span className={pill(row.status)}>{row.status}</span></td>
                  <td>{row.model || "-"}</td>
                  <td>{row.environment || "-"}</td>
                  <td>
                    <div>{row.user_id || "-"}</div>
                    <div style={{ color: "var(--muted)", fontSize: 12 }}>{row.session_id || "-"}</div>
                  </td>
                  <td>{Math.round((row.completion_rate || 0) * 100)}%</td>
                  <td>{decisionPill(row.decision?.action)}</td>
                  <td>{row.user_review_passed === null ? "-" : String(row.user_review_passed)}</td>
                  <td>{row.decision?.policy_version ? "Judge + Policy" : (row.model ? "possible" : "-")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="subtitle">Page {data.page} · Total {data.total}</p>
      </div>
    </div>
  );
}
