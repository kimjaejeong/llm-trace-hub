import Link from "next/link";
import { fetchApi } from "../../../components/api";
import LiveRefreshShell from "../../../components/live-refresh-shell";

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

function durationMs(start, end) {
  if (!start) return 0;
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(s) || Number.isNaN(e)) return 0;
  return Math.max(0, e - s);
}

function p95(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil(sorted.length * 0.95) - 1);
  return sorted[idx];
}

function fmtMs(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function asDate(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return "-";
  }
}

export default async function ProjectTraceDashboardPage({ params, searchParams }) {
  const { projectId } = await params;
  const query = await searchParams;
  const q = new URLSearchParams(query || {});
  q.set("page", q.get("page") || "1");
  q.set("page_size", q.get("page_size") || "10");
  const scopedHeaders = { "x-project-id": projectId };

  let data = { items: [], page: Number(q.get("page") || 1), page_size: 10, total: 0 };
  let stats = {
    window_hours: 24,
    totals: { open_traces: 0, success_traces: 0, error_traces: 0 },
    decisions: {},
    span_types: {},
    sampled_at: new Date().toISOString(),
  };
  let loadError = null;

  const [tracesRes, statsRes] = await Promise.allSettled([
    fetchApi(`/api/v1/traces?${q.toString()}`, { headers: scopedHeaders }),
    fetchApi("/api/v1/traces/stats/overview?last_hours=24", { headers: scopedHeaders }),
  ]);

  if (tracesRes.status === "fulfilled") {
    data = tracesRes.value;
  } else {
    loadError = tracesRes.reason?.message || "failed to load traces";
  }
  if (statsRes.status === "fulfilled") {
    stats = statsRes.value;
  } else if (!loadError) {
    loadError = `stats degraded: ${statsRes.reason?.message || "unavailable"}`;
  }

  const slaMs = 30000;
  const traceRows = data.items.map((row) => {
    const duration_ms = durationMs(row.start_time, row.end_time);
    const sla_breach = duration_ms >= slaMs;
    return { ...row, risk_score: riskScore(row), duration_ms, sla_breach };
  });
  const priorityQueue = [...traceRows]
    .filter((row) => row.sla_breach || row.status === "error" || row.risk_score >= 70)
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 6);

  const decisions = stats.decisions || {};
  const decisionTotal = Object.values(decisions).reduce((acc, cur) => acc + Number(cur || 0), 0);
  const totalTraces = Math.max(stats.totals.open_traces + stats.totals.success_traces + stats.totals.error_traces, 1);
  const errorRate = Math.round((stats.totals.error_traces / totalTraces) * 100);
  const escalationRate = Math.round((((decisions.ESCALATE || 0) + (decisions.BLOCK || 0)) / Math.max(decisionTotal, 1)) * 100);
  const p95Latency = p95(traceRows.map((r) => r.duration_ms));
  const breachCount = traceRows.filter((r) => r.sla_breach).length;
  const totalPages = Math.max(1, Math.ceil((data.total || 0) / Math.max(data.page_size || 10, 1)));
  const prevPage = Math.max(1, data.page - 1);
  const nextPage = Math.min(totalPages, data.page + 1);
  const prevQ = new URLSearchParams(query || {});
  prevQ.set("page", String(prevPage));
  prevQ.set("page_size", String(data.page_size || 10));
  const nextQ = new URLSearchParams(query || {});
  nextQ.set("page", String(nextPage));
  nextQ.set("page_size", String(data.page_size || 10));

  return (
    <div className="grid">
      {loadError ? (
        <div className="card alert-card">
          <h3 className="subhead">Fetch Error</h3>
          <p className="subtitle">{loadError}</p>
          {(String(loadError).includes("inactive") || String(loadError).includes("403")) ? (
            <div style={{ marginTop: 8 }}>
              <Link className="button detail-btn" href="/projects">Projects로 돌아가기</Link>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="card">
        <LiveRefreshShell label="Trace Control Room" />
        <h1 className="title">Realtime LLM Trace Control Room</h1>
        <p className="subtitle">핵심 운영 지표 기준: 오류율, 지연, SLA 위반, 우선 처리 큐.</p>
        <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
          <Link className="button detail-btn" href={`/projects/${projectId}/cases`}>Project Cases</Link>
        </div>

        <div className="stats-grid">
          <div className="stat"><div className="label">Open Traces</div><div className="value">{stats.totals.open_traces}</div></div>
          <div className="stat"><div className="label">Error Rate</div><div className="value">{errorRate}%</div></div>
          <div className="stat"><div className="label">Escalation Rate</div><div className="value">{escalationRate}%</div></div>
          <div className="stat"><div className="label">P95 Latency</div><div className="value">{fmtMs(p95Latency)}</div></div>
          <div className="stat"><div className="label">SLA Breach (30s)</div><div className="value">{breachCount}</div></div>
        </div>
      </div>

      <div className="card">
        <h3 className="subhead">Priority Queue</h3>
        <p className="subtitle">에러, SLA 위반, 고위험 트레이스 우선 처리 목록</p>
        {priorityQueue.length === 0 ? (
          <p className="subtitle" style={{ marginTop: 8 }}>No priority traces.</p>
        ) : (
          <div className="watchlist">
            {priorityQueue.map((row) => (
              <Link href={`/traces/${row.id}?project_id=${projectId}`} key={row.id} className="watch-item">
                <span className={riskPill(row.risk_score)}>{row.risk_score}</span>
                <span className="watch-id">{row.id}</span>
                <span className={pill(row.status)}>{row.status}</span>
                <span className={row.sla_breach ? "pill err" : "pill neutral"}>{row.sla_breach ? "SLA breach" : "within SLA"}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <form className="filters" method="get">
          <input className="input" name="status" placeholder="status" defaultValue={query?.status || ""} />
          <input className="input" name="model" placeholder="model" defaultValue={query?.model || ""} />
          <input className="input" name="environment" placeholder="environment" defaultValue={query?.environment || ""} />
          <input className="input" name="user_id" placeholder="user_id" defaultValue={query?.user_id || ""} />
          <input className="input" name="session_id" placeholder="session_id" defaultValue={query?.session_id || ""} />
          <input className="input" name="search" placeholder="input/output/logs search" defaultValue={query?.search || ""} />
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
                <th>Duration</th>
                <th>SLA</th>
                <th>Decision</th>
                <th>Risk</th>
                <th>Started</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {traceRows.map((row) => (
                <tr key={row.id}>
                  <td><Link href={`/traces/${row.id}?project_id=${projectId}`}>{row.id}</Link></td>
                  <td><span className={pill(row.status)}>{row.status}</span></td>
                  <td>{row.model || "-"}</td>
                  <td>{row.environment || "-"}</td>
                  <td>
                    <div>{row.user_id || "-"}</div>
                    <div style={{ color: "var(--muted)", fontSize: 12 }}>{row.session_id || "-"}</div>
                  </td>
                  <td>{fmtMs(row.duration_ms)}</td>
                  <td><span className={row.sla_breach ? "pill err" : "pill ok"}>{row.sla_breach ? "breach" : "ok"}</span></td>
                  <td>{decisionPill(row.decision?.action)}</td>
                  <td><span className={riskPill(row.risk_score)}>{row.risk_score}</span></td>
                  <td>{asDate(row.start_time)}</td>
                  <td><Link className="button detail-btn" href={`/traces/${row.id}?project_id=${projectId}`}>Tracing Detail</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pager">
          {data.page > 1 ? (
            <Link className="button" href={`/projects/${projectId}?${prevQ.toString()}`}>Prev</Link>
          ) : (
            <span className="button disabled">Prev</span>
          )}
          <span className="subtitle">Page {data.page} / {totalPages} · Total {data.total}</span>
          {data.page < totalPages ? (
            <Link className="button" href={`/projects/${projectId}?${nextQ.toString()}`}>Next</Link>
          ) : (
            <span className="button disabled">Next</span>
          )}
        </div>
      </div>
    </div>
  );
}
