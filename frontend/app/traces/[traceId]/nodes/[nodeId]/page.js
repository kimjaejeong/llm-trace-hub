import Link from "next/link";
import { fetchApi } from "../../../../../components/api";
import LiveRefreshShell from "../../../../../components/live-refresh-shell";

function asDate(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return String(ts || "-");
  }
}

function durationMs(start, end) {
  if (!start) return 0;
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(s) || Number.isNaN(e)) return 0;
  return Math.max(0, e - s);
}

function extractUsage(node, timeline) {
  const buckets = [];
  const attrUsage = node.attributes?.usage || node.attributes?.metadata?.token_usage;
  if (attrUsage) buckets.push(attrUsage);
  for (const item of timeline) {
    const payload = item.payload || {};
    if (payload.token_usage) buckets.push(payload.token_usage);
    if (payload.output_state?.token_usage) buckets.push(payload.output_state.token_usage);
  }

  let prompt = 0;
  let completion = 0;
  let total = 0;
  for (const u of buckets) {
    prompt += Number(u.prompt_tokens || u.input_tokens || 0);
    completion += Number(u.completion_tokens || u.output_tokens || 0);
    total += Number(u.total_tokens || 0);
  }
  if (!total) total = prompt + completion;
  return { prompt, completion, total };
}

function nodeCostEstimate(totalTokens) {
  // rough placeholder estimate for quick triage
  return (totalTokens / 1000) * 0.01;
}

export default async function TraceNodeDetailPage({ params, searchParams }) {
  const { traceId, nodeId } = await params;
  const qp = await searchParams;
  const projectId = qp?.project_id || "";
  const scopedHeaders = projectId ? { "x-project-id": projectId } : {};
  const data = await fetchApi(`/api/v1/traces/${traceId}`, { headers: scopedHeaders });
  const node = data.spans.find((s) => String(s.id) === String(nodeId));

  if (!node) {
    return (
      <div className="card">
        <h2 className="title" style={{ fontSize: 22 }}>Node Not Found</h2>
        <p className="subtitle">node_id={nodeId}</p>
        <p><Link href={`/traces/${traceId}${projectId ? `?project_id=${projectId}` : ""}`}>Back to Trace Detail</Link></p>
      </div>
    );
  }

  const nodeTimeline = data.timeline.filter((t) => String(t.source_id || "") === String(node.id));
  const usage = extractUsage(node, nodeTimeline);
  const ms = durationMs(node.start_time, node.end_time);
  const sourceRef = node.attributes?.metadata?.source_ref || {};
  const inputKeys = Object.keys(node.attributes?.input_state || {});
  const outputKeys = Object.keys(node.attributes?.output_state || {});

  return (
    <div className="grid">
      <div className="card">
        <LiveRefreshShell label={`Node ${node.attributes?.node_name || node.name}`} />
        <h1 className="title" style={{ fontSize: 28 }}>LangGraph Node Detail</h1>
        <p className="subtitle">
          Trace <Link href={`/traces/${traceId}${projectId ? `?project_id=${projectId}` : ""}`}>{traceId}</Link> · Node {node.id}
          {projectId ? ` · project_id ${projectId}` : ""}
        </p>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Runtime Stats</h3>
          <div className="kv"><div className="k">Name</div><div>{node.attributes?.node_name || node.name}</div></div>
          <div className="kv"><div className="k">Type</div><div>{node.attributes?.node_type || node.span_type}</div></div>
          <div className="kv"><div className="k">Status</div><div>{node.status}</div></div>
          <div className="kv"><div className="k">Started</div><div>{asDate(node.start_time)}</div></div>
          <div className="kv"><div className="k">Ended</div><div>{asDate(node.end_time)}</div></div>
          <div className="kv"><div className="k">Duration</div><div>{ms}ms</div></div>
          <div className="kv"><div className="k">Events</div><div>{nodeTimeline.length}</div></div>
          <div className="kv"><div className="k">Parent Span</div><div>{node.parent_span_id || "-"}</div></div>
        </div>

        <div className="card">
          <h3>Token Usage</h3>
          <div className="kv"><div className="k">Prompt Tokens</div><div>{usage.prompt}</div></div>
          <div className="kv"><div className="k">Completion Tokens</div><div>{usage.completion}</div></div>
          <div className="kv"><div className="k">Total Tokens</div><div>{usage.total}</div></div>
          <div className="kv"><div className="k">Cost Estimate</div><div>${nodeCostEstimate(usage.total).toFixed(4)}</div></div>
          <div className="kv"><div className="k">Input Keys</div><div>{inputKeys.join(", ") || "-"}</div></div>
          <div className="kv"><div className="k">Output Keys</div><div>{outputKeys.join(", ") || "-"}</div></div>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Source Mapping</h3>
          <div className="kv"><div className="k">File</div><div>{sourceRef.file || "-"}</div></div>
          <div className="kv"><div className="k">Line</div><div>{sourceRef.line || "-"}</div></div>
          <div className="kv"><div className="k">Function</div><div>{sourceRef.function || "-"}</div></div>
          <div className="kv"><div className="k">Metadata</div><div className="code">{JSON.stringify(node.attributes?.metadata || {}, null, 2)}</div></div>
        </div>
        <div className="card">
          <h3>State Snapshot</h3>
          <div className="code">input_state: {JSON.stringify(node.attributes?.input_state || {}, null, 2)}</div>
          <div className="code" style={{ marginTop: 8 }}>output_state: {JSON.stringify(node.attributes?.output_state || {}, null, 2)}</div>
        </div>
      </div>

      <div className="card">
        <h3>Node Timeline</h3>
        <div className="timeline">
          {nodeTimeline.map((item, idx) => (
            <div key={idx} className="timeline-item">
              <div style={{ fontWeight: 700 }}>{item.event_type}</div>
              <div style={{ color: "var(--muted)", fontSize: 12 }}>{asDate(item.timestamp)} · {item.source}</div>
              <div className="code" style={{ marginTop: 6 }}>{JSON.stringify(item.payload || {}, null, 2)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
