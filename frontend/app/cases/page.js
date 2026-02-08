import Link from "next/link";
import { fetchApi } from "../../components/api";

export default async function CasesPage({ searchParams }) {
  const params = await searchParams;
  const q = new URLSearchParams(params || {});
  q.set("page", q.get("page") || "1");
  q.set("page_size", q.get("page_size") || "10");
  const data = await fetchApi(`/api/v1/cases?${q.toString()}`);
  const totalPages = Math.max(1, Math.ceil((data.total || 0) / Math.max(data.page_size || 10, 1)));
  const prevQ = new URLSearchParams(params || {});
  prevQ.set("page", String(Math.max(1, data.page - 1)));
  prevQ.set("page_size", String(data.page_size || 10));
  const nextQ = new URLSearchParams(params || {});
  nextQ.set("page", String(Math.min(totalPages, data.page + 1)));
  nextQ.set("page_size", String(data.page_size || 10));
  const byStatus = data.stats?.by_status || {};

  return (
    <div className="grid">
      <div className="card">
        <h2 className="title" style={{ fontSize: 24 }}>Case Queue</h2>
        <p className="subtitle">Escalated traces are triaged here with assignee/status workflow.</p>
        <div className="stats-grid" style={{ marginTop: 10 }}>
          <div className="stat"><div className="label">Open</div><div className="value">{byStatus.open || 0}</div></div>
          <div className="stat"><div className="label">Acknowledged</div><div className="value">{byStatus.acknowledged || 0}</div></div>
          <div className="stat"><div className="label">Resolved</div><div className="value">{byStatus.resolved || 0}</div></div>
          <div className="stat"><div className="label">Overdue &gt;24h</div><div className="value">{data.stats?.overdue_open_24h || 0}</div></div>
        </div>
      </div>

      <div className="card">
        <form className="filters" method="get">
          <input className="input" name="status" placeholder="status" defaultValue={params?.status || ""} />
          <input className="input" name="assignee" placeholder="assignee" defaultValue={params?.assignee || ""} />
          <input className="input" name="reason_code" placeholder="reason_code" defaultValue={params?.reason_code || ""} />
          <button className="button" type="submit">Filter</button>
        </form>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Case</th><th>Trace</th><th>Reason</th><th>Status</th><th>Assignee</th><th>Created</th></tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id}>
                  <td><Link href={`/cases/${c.id}`}>{c.id}</Link></td>
                  <td><Link href={`/traces/${c.trace_id}`}>{c.trace_id}</Link></td>
                  <td>{c.reason_code}</td>
                  <td>{c.status}</td>
                  <td>{c.assignee || "-"}</td>
                  <td>{new Date(c.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pager">
          {data.page > 1 ? (
            <Link className="button" href={`/cases?${prevQ.toString()}`}>Prev</Link>
          ) : (
            <span className="button disabled">Prev</span>
          )}
          <span className="subtitle">Page {data.page} / {totalPages} · Total {data.total}</span>
          {data.page < totalPages ? (
            <Link className="button" href={`/cases?${nextQ.toString()}`}>Next</Link>
          ) : (
            <span className="button disabled">Next</span>
          )}
        </div>
      </div>
    </div>
  );
}
