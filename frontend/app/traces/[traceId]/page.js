import { fetchApi } from "../../../components/api";
import LiveRefreshShell from "../../../components/live-refresh-shell";

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

function stateDiffRows(nodes) {
  return nodes.map((node) => {
    const inKeys = Object.keys(node.attributes?.input_state || {});
    const outKeys = Object.keys(node.attributes?.output_state || {});
    const inSet = new Set(inKeys);
    const outSet = new Set(outKeys);
    const added = outKeys.filter((key) => !inSet.has(key));
    const removed = inKeys.filter((key) => !outSet.has(key));
    const kept = outKeys.filter((key) => inSet.has(key));
    return {
      id: node.id,
      name: node.attributes?.node_name || node.name,
      added,
      removed,
      kept,
    };
  });
}

function sourceRef(node) {
  return node.attributes?.metadata?.source_ref || null;
}

function formatDurationMs(start, end) {
  if (!start) return "-";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(s) || Number.isNaN(e)) return "-";
  return `${Math.max(0, e - s)}ms`;
}

function langGraphTopology(nodes) {
  const nodeMap = new Map(nodes.map((n) => [String(n.id), n]));
  const children = new Map();
  const indegree = new Map();

  for (const node of nodes) {
    const id = String(node.id);
    indegree.set(id, 0);
  }

  for (const node of nodes) {
    const id = String(node.id);
    const parent = node.parent_span_id ? String(node.parent_span_id) : null;
    if (parent && nodeMap.has(parent)) {
      if (!children.has(parent)) children.set(parent, []);
      children.get(parent).push(id);
      indegree.set(id, (indegree.get(id) || 0) + 1);
    }
  }

  const levelById = new Map();
  const queue = [];
  for (const [id, deg] of indegree.entries()) {
    if (deg === 0) {
      levelById.set(id, 0);
      queue.push(id);
    }
  }

  while (queue.length > 0) {
    const cur = queue.shift();
    const curLevel = levelById.get(cur) || 0;
    const childs = children.get(cur) || [];
    for (const child of childs) {
      const nextLevel = Math.max(levelById.get(child) || 0, curLevel + 1);
      levelById.set(child, nextLevel);
      queue.push(child);
    }
  }

  for (const node of nodes) {
    const id = String(node.id);
    if (!levelById.has(id)) levelById.set(id, 0);
  }

  const byLevel = new Map();
  for (const node of nodes) {
    const id = String(node.id);
    const lvl = levelById.get(id) || 0;
    if (!byLevel.has(lvl)) byLevel.set(lvl, []);
    byLevel.get(lvl).push(node);
  }

  const levels = [...byLevel.keys()].sort((a, b) => a - b);
  const boxW = 190;
  const boxH = 76;
  const xGap = 80;
  const yGap = 44;
  const margin = 24;

  const positioned = [];
  for (const lvl of levels) {
    const rows = byLevel.get(lvl) || [];
    rows.forEach((node, idx) => {
      positioned.push({
        ...node,
        x: margin + lvl * (boxW + xGap),
        y: margin + idx * (boxH + yGap),
      });
    });
  }

  const posMap = new Map(positioned.map((n) => [String(n.id), n]));
  const edges = [];
  for (const node of positioned) {
    const parent = node.parent_span_id ? String(node.parent_span_id) : null;
    if (parent && posMap.has(parent)) {
      const p = posMap.get(parent);
      edges.push({
        fromX: p.x + boxW,
        fromY: p.y + boxH / 2,
        toX: node.x,
        toY: node.y + boxH / 2,
      });
    }
  }

  const maxLevel = levels.length ? Math.max(...levels) : 0;
  const maxRows = Math.max(...[...byLevel.values()].map((arr) => arr.length), 1);
  const width = margin * 2 + (maxLevel + 1) * boxW + maxLevel * xGap;
  const height = margin * 2 + maxRows * boxH + (maxRows - 1) * yGap;

  return { nodes: positioned, edges, width, height, boxW, boxH };
}

export default async function TraceDetailPage({ params }) {
  const { traceId } = await params;
  const data = await fetchApi(`/api/v1/traces/${traceId}`);
  const graphNodes = data.spans.filter((s) => s.span_type === "langgraph_node");
  const tree = treeRows(data.spans);
  const diffs = stateDiffRows(graphNodes);
  const topology = langGraphTopology(graphNodes);
  const mappedNodes = graphNodes.filter((node) => !!sourceRef(node));
  const sourceCoverage = Math.round((mappedNodes.length / Math.max(graphNodes.length, 1)) * 100);
  const runningNodes = graphNodes.filter((node) => !node.end_time || node.status === "running");

  return (
    <div className="grid two">
      <div className="grid">
        <div className="card">
          <LiveRefreshShell label={`Trace ${traceId}`} />
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
          <h3>LangGraph Live Nodes</h3>
          <p className="subtitle">
            Running {runningNodes.length}/{graphNodes.length} nodes · auto refresh enabled
          </p>
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="table">
              <thead><tr><th>Node</th><th>Status</th><th>Duration</th><th>Updated</th></tr></thead>
              <tbody>
                {graphNodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.attributes?.node_name || node.name}</td>
                    <td><span className={pill(node.status)}>{node.status}</span></td>
                    <td>{formatDurationMs(node.start_time, node.end_time)}</td>
                    <td>{asDate(node.end_time || node.start_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h3>LangGraph Node-Edge Graph</h3>
          <p className="subtitle">Node topology reconstructed from parent-child spans in this trace.</p>
          <div className="graph-canvas-wrap">
            <svg className="graph-canvas" viewBox={`0 0 ${topology.width} ${topology.height}`} preserveAspectRatio="xMinYMin meet">
              <defs>
                <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#8aa0b8" />
                </marker>
              </defs>
              {topology.edges.map((edge, idx) => (
                <line
                  key={idx}
                  x1={edge.fromX}
                  y1={edge.fromY}
                  x2={edge.toX}
                  y2={edge.toY}
                  stroke="#8aa0b8"
                  strokeWidth="1.6"
                  markerEnd="url(#arrowhead)"
                />
              ))}
              {topology.nodes.map((node) => (
                <g key={node.id}>
                  <rect
                    x={node.x}
                    y={node.y}
                    width={topology.boxW}
                    height={topology.boxH}
                    rx="12"
                    fill="#ffffff"
                    stroke="#cdd8e8"
                  />
                  <text x={node.x + 10} y={node.y + 24} fontSize="12" fontWeight="700" fill="#132742">
                    {(node.attributes?.node_name || node.name || "").slice(0, 25)}
                  </text>
                  <text x={node.x + 10} y={node.y + 42} fontSize="11" fill="#5f7188">
                    {(node.attributes?.node_type || "-").slice(0, 20)}
                  </text>
                  <text x={node.x + 10} y={node.y + 60} fontSize="11" fill="#5f7188">
                    {String(node.status).slice(0, 20)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </div>

        <div className="card">
          <h3>LangGraph Nodes ({graphNodes.length})</h3>
          <p className="subtitle">Source mapped {mappedNodes.length}/{graphNodes.length} ({sourceCoverage}%)</p>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Node</th><th>Type</th><th>Status</th><th>Source</th><th>State Keys</th></tr></thead>
              <tbody>
                {graphNodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.attributes?.node_name || node.name}</td>
                    <td>{node.attributes?.node_type || "-"}</td>
                    <td><span className={pill(node.status)}>{node.status}</span></td>
                    <td>
                      {sourceRef(node) ? (
                        <div>
                          <div><span className="pill ok">mapped</span></div>
                          <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
                            {sourceRef(node).file}:{sourceRef(node).line} · {sourceRef(node).function}
                          </div>
                        </div>
                      ) : (
                        <span className="pill warn">unmapped</span>
                      )}
                    </td>
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

        <div className="card">
          <h3>LangGraph Source Coverage (custom)</h3>
          <div className="kv"><div className="k">Coverage</div><div>{sourceCoverage}%</div></div>
          <div className="kv"><div className="k">Mapped Nodes</div><div>{mappedNodes.length}</div></div>
          <div className="kv"><div className="k">Unmapped Nodes</div><div>{Math.max(graphNodes.length - mappedNodes.length, 0)}</div></div>
          <div className="kv"><div className="k">Check Rule</div><div>`metadata.source_ref` exists per node</div></div>
        </div>

        <div className="card">
          <h3>State Transition Diff (custom)</h3>
          <p className="subtitle">Keys introduced/removed per LangGraph node, for state-shape drift detection.</p>
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="table">
              <thead><tr><th>Node</th><th>Added Keys</th><th>Removed Keys</th><th>Stable Keys</th></tr></thead>
              <tbody>
                {diffs.map((d) => (
                  <tr key={d.id}>
                    <td>{d.name}</td>
                    <td>{d.added.join(", ") || "-"}</td>
                    <td>{d.removed.join(", ") || "-"}</td>
                    <td>{d.kept.join(", ") || "-"}</td>
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
