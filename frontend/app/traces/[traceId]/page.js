import { fetchApi } from "../../../components/api";

function renderJson(data) {
  return <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre>;
}

export default async function TraceDetailPage({ params }) {
  const { traceId } = await params;
  const data = await fetchApi(`/api/v1/traces/${traceId}`);

  return (
    <div className="grid two">
      <div className="card">
        <h2>Trace Detail</h2>
        {renderJson(data.trace)}
        <h3>Span Tree</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Span</th><th>Parent</th><th>Type</th><th>Status</th><th>Time</th>
            </tr>
          </thead>
          <tbody>
            {data.spans.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>{s.parent_span_id || "root"}</td>
                <td>{s.span_type}</td>
                <td>{s.status}</td>
                <td>{new Date(s.start_time).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Timeline</h3>
        <table className="table">
          <thead>
            <tr><th>At</th><th>Type</th><th>Source</th></tr>
          </thead>
          <tbody>
            {data.timeline.map((t, idx) => (
              <tr key={idx}>
                <td>{new Date(t.timestamp).toLocaleString()}</td>
                <td>{t.event_type}</td>
                <td>{t.source}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>Evaluations</h3>
        {renderJson(data.evaluations)}

        <h3>Decision / Judge Runs</h3>
        {renderJson({ decision_history: data.decision_history, judge_runs: data.judge_runs })}
      </div>
    </div>
  );
}
