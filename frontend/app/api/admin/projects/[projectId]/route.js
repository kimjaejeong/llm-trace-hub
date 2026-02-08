import { proxyToBackend } from "../../_utils";

export async function DELETE(_request, { params }) {
  const { projectId } = await params;
  return proxyToBackend(`/api/v1/projects/${projectId}`, {
    method: "DELETE",
  });
}
