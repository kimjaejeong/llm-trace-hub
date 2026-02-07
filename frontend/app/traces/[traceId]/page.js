import { fetchApi } from "../../../components/api";

function pill(status) {
  if (status === "success") return "pill ok";
  if (status === "error") return "pill err";
  return "pill warn";
}

function asDate(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return String(ts || "-");
  }
}

function treeRows(spans) {
  const children = new Map();
  for (const span of spans) {
    const key = span.parent_span_id || "root";
    if (!children.has(key)) children.set(key, []);
    children.get(key).push(span);
  }

  const rows = [];
  function walk(parentId, depth) {
    const nodes = children.get(parentId) || [];
    for (const node of nodes) {
      rows.push({ node, depth });
      walk(node.id, depth + 1);
    }
  }
  walk("root", 0);
  return rows;
}

export default async function TraceDetailPage({ params }) {
  const { traceId } = await params;
  const data = await fetchApi(`/api/v1/traces/${traceId}`);
  const graphNodes = data.spans.filter((s) => s.span_type === "langgraph_node");
  const tree = treeRows(data.spans);

  return (
    <div className="grid two">
      <div className="grid">
        <div className="card">
          <h1 className="title">Trace Detail</h1>
          <div className="kv"><div className="k">trace_id</div><div>{data.trace.id}</div></div>
          <div className="kv"><div className="k">status</div><div><span className={pill(data.trace.status)}>{data.trace.status}</span></div></div>
          <div className="kv"><div className="k">decision</div><div>{data.trace.decision?.action || "none"}</div></div>
          <div className="kv"><div className="k">user_review</div><div>{String(data.trace.user_review_passed)}</div></div>
          <div className="kv"><div className="k">completion</div><div>{Math.round((data.trace.completion_rate || 0) * 100)}%</div></div>
          <div className="kv"><div className="k">model/env</div><div>{data.trace.model || "-"} / {data.trace.environment || "-"}</div></div>
        </div>

        <div className="card">
          <h3>Span Tree</h3>
          <ul className="tree">
            {tree.map(({ node, depth }) => (
              <li key={node.id} style={{ marginLeft: depth * 14 }}>
                <div className="node-head">
                  <span className={pill(node.status)}>{node.status}</span>
                  <span>{node.name}</span>
                  <span style={{ color: "var(--muted)", fontSize: 12 }}>({node.span_type})</span>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{asDate(node.start_time)} → {asDate(node.end_time)}</div>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>LangGraph Nodes ({graphNodes.length})</h3>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Node</th><th>Type</th><th>Status</th><th>State Keys</th></tr></thead>
              <tbody>
                {graphNodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.attributes?.node_name || node.name}</td>
                    <td>{node.attributes?.node_type || "-"}</td>
                    <td><span className={pill(node.status)}>{node.status}</span></td>
                    <td>
                      in: {(Object.keys(node.attributes?.input_state || {})).join(", ") || "-"}
                      <br />
                      out: {(Object.keys(node.attributes?.output_state || {})).join(", ") || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Timeline</h3>
          <div className="timeline">
            {data.timeline.map((t, idx) => (
              <div key={idx} className="timeline-item">
                <div style={{ fontWeight: 700 }}>{t.event_type}</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{asDate(t.timestamp)} · {t.source}</div>
                <div className="code" style={{ marginTop: 6 }}>{JSON.stringify(t.payload || {}, null, 2)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Evaluations</h3>
          <div className="code">{JSON.stringify(data.evaluations, null, 2)}</div>
        </div>

        <div className="card">
          <h3>Decision + Judge Runs</h3>
          <div className="code">{JSON.stringify({ decision_history: data.decision_history, judge_runs: data.judge_runs }, null, 2)}</div>
        </div>
      </div>
    </div>
  );
}
