import Link from "next/link";
import { fetchApi } from "../../../../components/api";

export default async function ProjectCasesPage({ params, searchParams }) {
  const { projectId } = await params;
  const query = await searchParams;
  const q = new URLSearchParams(query || {});
  q.set("page", q.get("page") || "1");
  q.set("page_size", q.get("page_size") || "10");

  const data = await fetchApi(`/api/v1/cases?${q.toString()}`, {
    headers: { "x-project-id": projectId },
  });

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / Math.max(data.page_size || 10, 1)));
  const prevQ = new URLSearchParams(query || {});
  prevQ.set("page", String(Math.max(1, data.page - 1)));
  prevQ.set("page_size", String(data.page_size || 10));
  const nextQ = new URLSearchParams(query || {});
  nextQ.set("page", String(Math.min(totalPages, data.page + 1)));
  nextQ.set("page_size", String(data.page_size || 10));
  const byStatus = data.stats?.by_status || {};

  return (
    <div className="grid">
      <div className="card">
        <h2 className="title" style={{ fontSize: 24 }}>Case Queue</h2>
        <p className="subtitle">Escalated traces are triaged here with assignee/status workflow.</p>
        <div className="stats-grid" style={{ marginTop: 10 }}>
          <div className="stat"><div className="label">Open</div><div className="value">{byStatus.open || 0}</div></div>
          <div className="stat"><div className="label">Acknowledged</div><div className="value">{byStatus.acknowledged || 0}</div></div>
          <div className="stat"><div className="label">Resolved</div><div className="value">{byStatus.resolved || 0}</div></div>
          <div className="stat"><div className="label">Overdue &gt;24h</div><div className="value">{data.stats?.overdue_open_24h || 0}</div></div>
        </div>
      </div>

      <div className="card">
        <h3 className="subhead">Cases Template Examples</h3>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead><tr><th>Reason Code</th><th>When To Trigger</th><th>Recommended Action</th></tr></thead>
            <tbody>
              <tr><td>PII_DETECTED</td><td>개인정보(주민번호, 카드번호 등) 노출 신호</td><td>즉시 Ack 후 민감정보 마스킹/차단</td></tr>
              <tr><td>POLICY_VIOLATION</td><td>금지 도메인 답변, 안전정책 위반</td><td>Resolve 전에 정책 버전/프롬프트 수정 검토</td></tr>
              <tr><td>HIGH_HALLUCINATION_RISK</td><td>근거 없는 답변 + 낮은 confidence</td><td>근거 retrieval 강화 후 재실행</td></tr>
              <tr><td>SLA_BREACH</td><td>30s 이상 지연이 반복</td><td>병목 노드 확인 후 모델/툴 타임아웃 조정</td></tr>
              <tr><td>TOOL_FAILURE</td><td>외부 API/DB 툴 오류율 상승</td><td>온콜 에스컬레이션 + fallback 경로 활성화</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <form className="filters" method="get">
          <input className="input" name="status" placeholder="status" defaultValue={query?.status || ""} />
          <input className="input" name="assignee" placeholder="assignee" defaultValue={query?.assignee || ""} />
          <input className="input" name="reason_code" placeholder="reason_code" defaultValue={query?.reason_code || ""} />
          <button className="button" type="submit">Filter</button>
        </form>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Case</th><th>Trace</th><th>Reason</th><th>Status</th><th>Assignee</th><th>Created</th></tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id}>
                  <td><Link href={`/cases/${c.id}?project_id=${projectId}`}>{c.id}</Link></td>
                  <td><Link href={`/traces/${c.trace_id}?project_id=${projectId}`}>{c.trace_id}</Link></td>
                  <td>{c.reason_code}</td>
                  <td>{c.status}</td>
                  <td>{c.assignee || "-"}</td>
                  <td>{new Date(c.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pager">
          {data.page > 1 ? (
            <Link className="button" href={`/projects/${projectId}/cases?${prevQ.toString()}`}>Prev</Link>
          ) : (
            <span className="button disabled">Prev</span>
          )}
          <span className="subtitle">Page {data.page} / {totalPages} · Total {data.total}</span>
          {data.page < totalPages ? (
            <Link className="button" href={`/projects/${projectId}/cases?${nextQ.toString()}`}>Next</Link>
          ) : (
            <span className="button disabled">Next</span>
          )}
        </div>
      </div>
    </div>
  );
}
