import { proxyToBackend } from "../../../_utils";

export async function GET(_request, { params }) {
  const { projectId } = await params;
  return proxyToBackend(`/api/v1/projects/${projectId}/current-key`);
}
