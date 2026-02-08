import Link from "next/link";
import { fetchApi } from "../components/api";
import LiveRefreshShell from "../components/live-refresh-shell";

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

function riskScore(row) {
  let score = 0;
  if (row.status === "error") score += 55;
  if (row.has_open_spans) score += 20;
  if (row.decision?.action === "ESCALATE") score += 25;
  if (row.decision?.action === "BLOCK") score += 35;
  if (row.user_review_passed === false) score += 20;
  const completion = Math.round((row.completion_rate || 0) * 100);
  score += Math.max(0, Math.round((100 - completion) * 0.2));
  return Math.min(100, score);
}

function riskPill(score) {
  if (score >= 75) return "pill err";
  if (score >= 45) return "pill warn";
  return "pill ok";
}

function asDate(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return "-";
  }
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

  const traceRows = data.items.map((row) => ({ ...row, risk_score: riskScore(row) }));
  const watchlist = [...traceRows].filter((row) => row.risk_score >= 40).sort((a, b) => b.risk_score - a.risk_score).slice(0, 5);

  const decisions = stats.decisions || {};
  const decisionTotal = Object.values(decisions).reduce((acc, cur) => acc + Number(cur || 0), 0);
  const allowRate = Math.round(((decisions.ALLOW_ANSWER || 0) / Math.max(decisionTotal, 1)) * 100);
  const pressureIndex = Math.round(
    ((stats.totals.error_traces + (decisions.ESCALATE || 0) + (decisions.BLOCK || 0)) /
      Math.max(stats.totals.open_traces + stats.totals.success_traces + stats.totals.error_traces, 1)) *
      100
  );
  const reviewed = traceRows.filter((row) => row.user_review_passed !== null);
  const reviewGap = Math.round(
    (reviewed.filter((row) => row.user_review_passed === false).length / Math.max(reviewed.length, 1)) * 100
  );

  return (
    <div className="grid">
      <div className="card">
        <LiveRefreshShell label="Trace Control Room" />
        <h1 className="title">Realtime LLM Trace Control Room</h1>
        <p className="subtitle">
          LangGraph node tracing, decision outcomes, and operator-first triage in one view.
        </p>

        <div className="stats-grid">
          <div className="stat"><div className="label">Open Traces</div><div className="value">{stats.totals.open_traces}</div></div>
          <div className="stat"><div className="label">Success</div><div className="value">{stats.totals.success_traces}</div></div>
          <div className="stat"><div className="label">Errors</div><div className="value">{stats.totals.error_traces}</div></div>
          <div className="stat"><div className="label">Escalations</div><div className="value">{stats.decisions.ESCALATE || 0}</div></div>
          <div className="stat"><div className="label">LangGraph Nodes</div><div className="value">{stats.span_types.langgraph_node || 0}</div></div>
          <div className="stat"><div className="label">Guardrail Pressure</div><div className="value">{pressureIndex}%</div></div>
          <div className="stat"><div className="label">Autonomy Index</div><div className="value">{allowRate}%</div></div>
          <div className="stat"><div className="label">Review Gap</div><div className="value">{reviewGap}%</div></div>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3 className="subhead">AI Watchlist</h3>
          <p className="subtitle">Auto-ranked traces by risk score (custom feature).</p>
          {watchlist.length === 0 ? (
            <p className="subtitle" style={{ marginTop: 8 }}>No active high-risk traces.</p>
          ) : (
            <div className="watchlist">
              {watchlist.map((row) => (
                <Link href={`/traces/${row.id}`} key={row.id} className="watch-item">
                  <span className={riskPill(row.risk_score)}>{row.risk_score}</span>
                  <span className="watch-id">{row.id}</span>
                  <span className={pill(row.status)}>{row.status}</span>
                  <span>{row.decision?.action || "no-decision"}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="card">
          <h3 className="subhead">Now</h3>
          <div className="kv"><div className="k">Sample Window</div><div>{stats.window_hours}h rolling</div></div>
          <div className="kv"><div className="k">Sampled At</div><div>{asDate(stats.sampled_at)}</div></div>
          <div className="kv"><div className="k">Top Action</div><div>{Object.entries(decisions).sort((a, b) => b[1] - a[1])[0]?.[0] || "-"}</div></div>
          <div className="kv"><div className="k">Decision Volume</div><div>{decisionTotal}</div></div>
          <div className="kv"><div className="k">Feature Flag</div><div>Risk Scoring + Watchlist enabled</div></div>
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
                <th>Risk</th>
                <th>LangGraph</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {traceRows.map((row) => (
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
                  <td><span className={riskPill(row.risk_score)}>{row.risk_score}</span></td>
                  <td>{row.decision?.policy_version ? "Judge + Policy" : (row.model ? "possible" : "-")}</td>
                  <td>{asDate(row.start_time)}</td>
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
