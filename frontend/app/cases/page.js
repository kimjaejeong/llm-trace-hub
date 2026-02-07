import Link from "next/link";
import { fetchApi } from "../../components/api";

export default async function CasesPage({ searchParams }) {
  const params = await searchParams;
  const q = new URLSearchParams(params || {});
  const data = await fetchApi(`/api/v1/cases?${q.toString()}`);

  return (
    <div className="card">
      <h2>Cases</h2>
      <form className="filters" method="get">
        <input className="input" name="status" placeholder="open/acknowledged/resolved" defaultValue={params?.status || ""} />
        <button className="input" type="submit">Filter</button>
      </form>
      <table className="table">
        <thead>
          <tr><th>Case</th><th>Trace</th><th>Reason</th><th>Status</th><th>Assignee</th><th>Created</th></tr>
        </thead>
        <tbody>
          {data.map((c) => (
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
  );
}
