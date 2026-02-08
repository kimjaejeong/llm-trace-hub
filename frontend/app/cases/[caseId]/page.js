import Link from "next/link";
import { fetchApi } from "../../../components/api";
import CaseActions from "../../../components/case-actions";

function elapsedHours(start, end) {
  if (!start) return "-";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(s) || Number.isNaN(e)) return "-";
  return `${((e - s) / (1000 * 60 * 60)).toFixed(1)}h`;
}

export default async function CaseDetailPage({ params }) {
  const { caseId } = await params;
  const data = await fetchApi(`/api/v1/cases/${caseId}`);
  const trace = await fetchApi(`/api/v1/traces/${data.trace_id}`);

  return (
    <div className="grid">
      <div className="card">
        <h2 className="title" style={{ fontSize: 24 }}>Case Detail</h2>
        <p className="subtitle">Escalation workflow for one trace.</p>
      </div>
      <div className="grid two">
        <div className="card">
          <div className="kv"><div className="k">Case ID</div><div>{data.id}</div></div>
          <div className="kv"><div className="k">Trace</div><div><Link href={`/traces/${data.trace_id}`}>{data.trace_id}</Link></div></div>
          <div className="kv"><div className="k">Reason</div><div>{data.reason_code}</div></div>
          <div className="kv"><div className="k">Status</div><div>{data.status}</div></div>
          <div className="kv"><div className="k">Assignee</div><div>{data.assignee || "-"}</div></div>
          <div className="kv"><div className="k">Created</div><div>{new Date(data.created_at).toLocaleString()}</div></div>
          <div className="kv"><div className="k">Age</div><div>{elapsedHours(data.created_at, data.resolved_at)}</div></div>
          <div style={{ marginTop: 14 }}>
            <CaseActions caseId={caseId} />
          </div>
        </div>

        <div className="card">
          <h3>Trace Context</h3>
          <div className="kv"><div className="k">Trace Status</div><div>{trace.trace.status}</div></div>
          <div className="kv"><div className="k">Decision</div><div>{trace.trace.decision?.action || "-"}</div></div>
          <div className="kv"><div className="k">Model</div><div>{trace.trace.model || "-"}</div></div>
          <div className="kv"><div className="k">Environment</div><div>{trace.trace.environment || "-"}</div></div>
          <div className="kv"><div className="k">Completion</div><div>{Math.round((trace.trace.completion_rate || 0) * 100)}%</div></div>
          <div className="kv"><div className="k">Open Spans</div><div>{String(trace.trace.has_open_spans)}</div></div>
          <div style={{ marginTop: 12 }}>
            <Link className="button" href={`/traces/${data.trace_id}`}>Open Trace Detail</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
