import { proxyToBackend } from "../../../_utils";

export async function POST(_request, { params }) {
  const { projectId } = await params;
  return proxyToBackend(`/api/v1/projects/${projectId}/rotate-key`, {
    method: "POST",
  });
}
