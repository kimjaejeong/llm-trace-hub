import Link from "next/link";
import { fetchApi } from "../../../components/api";
import CaseActions from "../../../components/case-actions";

export default async function CaseDetailPage({ params }) {
  const { caseId } = await params;
  const data = await fetchApi(`/api/v1/cases/${caseId}`);

  return (
    <div className="card">
      <h2>Case Detail</h2>
      <p><b>Case ID:</b> {data.id}</p>
      <p><b>Trace:</b> <Link href={`/traces/${data.trace_id}`}>{data.trace_id}</Link></p>
      <p><b>Reason:</b> {data.reason_code}</p>
      <p><b>Status:</b> {data.status}</p>
      <p><b>Assignee:</b> {data.assignee || "-"}</p>
      <p><b>Created:</b> {new Date(data.created_at).toLocaleString()}</p>
      <CaseActions caseId={caseId} />
    </div>
  );
}
