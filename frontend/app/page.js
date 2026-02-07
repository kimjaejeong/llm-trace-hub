import Link from "next/link";
import { fetchApi } from "../components/api";

function badgeClass(status) {
  if (status === "success") return "badge ok";
  if (status === "error") return "badge err";
  return "badge warn";
}

export default async function TracesPage({ searchParams }) {
  const params = await searchParams;
  const q = new URLSearchParams(params || {});
  const page = q.get("page") || "1";
  q.set("page", page);
  q.set("page_size", q.get("page_size") || "20");

  const data = await fetchApi(`/api/v1/traces?${q.toString()}`);

  return (
    <div className="grid">
      <div className="card">
        <h2>Trace List</h2>
        <form className="filters" method="get">
          <input className="input" name="status" placeholder="status" defaultValue={params?.status || ""} />
          <input className="input" name="model" placeholder="model" defaultValue={params?.model || ""} />
          <input className="input" name="environment" placeholder="environment" defaultValue={params?.environment || ""} />
          <input className="input" name="user_id" placeholder="user_id" defaultValue={params?.user_id || ""} />
          <input className="input" name="session_id" placeholder="session_id" defaultValue={params?.session_id || ""} />
          <input className="input" name="search" placeholder="input/output/logs search" defaultValue={params?.search || ""} />
          <button className="input" type="submit">Filter</button>
        </form>

        <table className="table">
          <thead>
            <tr>
              <th>Trace</th>
              <th>Status</th>
              <th>Model</th>
              <th>Environment</th>
              <th>User</th>
              <th>Completion</th>
              <th>Decision</th>
              <th>User Review</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.id}>
                <td><Link href={`/traces/${row.id}`}>{row.id}</Link></td>
                <td><span className={badgeClass(row.status)}>{row.status}</span></td>
                <td>{row.model || "-"}</td>
                <td>{row.environment || "-"}</td>
                <td>{row.user_id || "-"}</td>
                <td>{Math.round((row.completion_rate || 0) * 100)}%</td>
                <td>{row.decision?.action || "-"}</td>
                <td>{String(row.user_review_passed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>Page {data.page} / total {data.total}</p>
      </div>
    </div>
  );
}
