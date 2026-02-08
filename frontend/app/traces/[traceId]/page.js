import Link from "next/link";
import { fetchApi } from "../../../components/api";
import LiveRefreshShell from "../../../components/live-refresh-shell";
import LangGraphGraph from "../../../components/langgraph-graph";

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

function spanDurationMs(span) {
  if (!span?.start_time) return 0;
  const s = new Date(span.start_time).getTime();
  const e = span.end_time ? new Date(span.end_time).getTime() : Date.now();
  if (Number.isNaN(s) || Number.isNaN(e)) return 0;
  return Math.max(0, e - s);
}

function criticalPath(spans) {
  const children = new Map();
  const byId = new Map();
  for (const span of spans) {
    byId.set(String(span.id), span);
    const key = span.parent_span_id ? String(span.parent_span_id) : "root";
    if (!children.has(key)) children.set(key, []);
    children.get(key).push(span);
  }

  let best = { total: 0, path: [] };
  function dfs(node, acc, path) {
    const dur = spanDurationMs(node);
    const nextAcc = acc + dur;
    const nextPath = [...path, { id: node.id, name: node.name, span_type: node.span_type, duration_ms: dur }];
    const kids = children.get(String(node.id)) || [];
    if (!kids.length && nextAcc > best.total) best = { total: nextAcc, path: nextPath };
    for (const child of kids) dfs(child, nextAcc, nextPath);
  }

  const roots = children.get("root") || [];
  for (const root of roots) dfs(root, 0, []);
  return best;
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

function nodeHref(traceId, nodeId) {
  return `/traces/${traceId}/nodes/${nodeId}`;
}

export default async function TraceDetailPage({ params }) {
  const { traceId } = await params;

  let data = {
    trace: { id: traceId, status: "unknown", completion_rate: 0 },
    spans: [],
    timeline: [],
    evaluations: [],
    decision_history: [],
    judge_runs: [],
  };
  let loadError = null;
  try {
    data = await fetchApi(`/api/v1/traces/${traceId}`);
  } catch (err) {
    loadError = err?.message || "failed to load trace detail";
  }

  const graphNodes = data.spans.filter((s) => s.span_type === "langgraph_node");
  const tree = treeRows(data.spans);
  const diffs = stateDiffRows(graphNodes);
  const topology = langGraphTopology(graphNodes);
  const mappedNodes = graphNodes.filter((node) => !!sourceRef(node));
  const sourceCoverage = Math.round((mappedNodes.length / Math.max(graphNodes.length, 1)) * 100);
  const runningNodes = graphNodes.filter((node) => !node.end_time || node.status === "running");
  const cp = criticalPath(data.spans);

  return (
    <div className="grid">
      {loadError ? (
        <div className="card alert-card">
          <h3 className="subhead">Fetch Error</h3>
          <p className="subtitle">{loadError}</p>
        </div>
      ) : null}

      <div className="card">
        <LiveRefreshShell label={`Trace ${traceId}`} />
        <h1 className="title">Trace Detail</h1>
        <div className="grid two">
          <div>
            <div className="kv"><div className="k">trace_id</div><div>{data.trace.id}</div></div>
            <div className="kv"><div className="k">status</div><div><span className={pill(data.trace.status)}>{data.trace.status}</span></div></div>
            <div className="kv"><div className="k">completion</div><div>{Math.round((data.trace.completion_rate || 0) * 100)}%</div></div>
          </div>
          <div>
            <div className="kv"><div className="k">decision</div><div>{data.trace.decision?.action || "none"}</div></div>
            <div className="kv"><div className="k">review</div><div>{String(data.trace.user_review_passed)}</div></div>
            <div className="kv"><div className="k">model/env</div><div>{data.trace.model || "-"} / {data.trace.environment || "-"}</div></div>
          </div>
        </div>
      </div>

      <h3 className="section-title">Runtime Flow</h3>
      <div className="grid">
        <div className="card">
          <h3>Execution Hot Path (must-have)</h3>
          <div className="kv"><div className="k">Total Duration</div><div>{formatDurationMs(data.trace.start_time, data.trace.end_time)}</div></div>
          <div className="kv"><div className="k">Critical Path</div><div>{cp.total}ms</div></div>
          <div className="kv"><div className="k">Nodes In Path</div><div>{cp.path.length}</div></div>
          <div className="path-row">
            {cp.path.map((item, idx) => (
              <span key={item.id} className="path-node">
                {item.name} ({item.duration_ms}ms){idx < cp.path.length - 1 ? " -> " : ""}
              </span>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>LangGraph Live Nodes</h3>
          <p className="subtitle">Running {runningNodes.length}/{graphNodes.length} nodes</p>
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="table">
              <thead><tr><th>Node</th><th>Status</th><th>Duration</th><th>Updated</th><th>Inspect</th></tr></thead>
              <tbody>
                {graphNodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.attributes?.node_name || node.name}</td>
                    <td><span className={pill(node.status)}>{node.status}</span></td>
                    <td>{formatDurationMs(node.start_time, node.end_time)}</td>
                    <td>{asDate(node.end_time || node.start_time)}</td>
                    <td><Link className="button detail-btn" href={nodeHref(traceId, node.id)}>Node Detail</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h3>LangGraph Node-Edge Graph</h3>
          <p className="subtitle">클릭으로 노드 상세 이동, 크게 보기/접기 지원.</p>
          <LangGraphGraph traceId={traceId} topology={topology} />
        </div>
      </div>

      <h3 className="section-title">Node Diagnostics</h3>
      <div className="card">
        <div className="kv"><div className="k">Source Coverage</div><div>{mappedNodes.length}/{graphNodes.length} ({sourceCoverage}%)</div></div>
        <details style={{ marginTop: 10 }}>
          <summary className="subtitle">Node Inventory</summary>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table className="table">
              <thead><tr><th>Node</th><th>Type</th><th>Status</th><th>Source</th><th>Inspect</th></tr></thead>
              <tbody>
                {graphNodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.attributes?.node_name || node.name}</td>
                    <td>{node.attributes?.node_type || "-"}</td>
                    <td><span className={pill(node.status)}>{node.status}</span></td>
                    <td>
                      {sourceRef(node) ? (
                        <div style={{ color: "var(--muted)", fontSize: 12 }}>
                          {sourceRef(node).file}:{sourceRef(node).line}
                        </div>
                      ) : (
                        <span className="pill warn">unmapped</span>
                      )}
                    </td>
                    <td><Link className="button detail-btn" href={nodeHref(traceId, node.id)}>Node Detail</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        <details style={{ marginTop: 10 }}>
          <summary className="subtitle">State Transition Diff</summary>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table className="table">
              <thead><tr><th>Node</th><th>Added</th><th>Removed</th><th>Stable</th></tr></thead>
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
        </details>
      </div>

      <h3 className="section-title">Governance And Audit</h3>
      <div className="grid two">
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
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{asDate(node.start_time)} to {asDate(node.end_time)}</div>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>Timeline</h3>
          <div className="timeline">
            {data.timeline.map((t, idx) => (
              <div key={idx} className="timeline-item">
                <div style={{ fontWeight: 700 }}>{t.event_type}</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{asDate(t.timestamp)} · {t.source}</div>
                <details style={{ marginTop: 6 }}>
                  <summary className="subtitle">payload</summary>
                  <div className="code" style={{ marginTop: 6 }}>{JSON.stringify(t.payload || {}, null, 2)}</div>
                </details>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Evaluations</h3>
          <details>
            <summary className="subtitle">Expand</summary>
            <div className="code" style={{ marginTop: 8 }}>{JSON.stringify(data.evaluations, null, 2)}</div>
          </details>
        </div>
        <div className="card">
          <h3>Decision And Judge Runs</h3>
          <details>
            <summary className="subtitle">Expand</summary>
            <div className="code" style={{ marginTop: 8 }}>{JSON.stringify({ decision_history: data.decision_history, judge_runs: data.judge_runs }, null, 2)}</div>
          </details>
        </div>
      </div>
    </div>
  );
}
