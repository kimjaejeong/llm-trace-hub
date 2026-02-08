import { proxyToBackend } from "../_utils";

export async function GET() {
  return proxyToBackend("/api/v1/projects");
}

export async function POST(request) {
  const body = await request.text();
  return proxyToBackend("/api/v1/projects", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
}
