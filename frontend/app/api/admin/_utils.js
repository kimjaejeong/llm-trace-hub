import { NextResponse } from "next/server";

function backendBases() {
  const values = [
    process.env.BACKEND_URL,
    process.env.NEXT_PUBLIC_BACKEND_URL,
    "http://backend:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
  ];
  return values.filter(Boolean);
}

function adminKey() {
  return (
    process.env.ADMIN_KEY ||
    process.env.API_KEY ||
    process.env.NEXT_PUBLIC_ADMIN_KEY ||
    process.env.NEXT_PUBLIC_API_KEY ||
    "dev-key"
  );
}

export async function proxyToBackend(path, init = {}) {
  let lastErr = null;
  for (const base of backendBases()) {
    try {
      const res = await fetch(`${base}${path}`, {
        ...init,
        headers: {
          "x-api-key": adminKey(),
          ...(init.headers || {}),
        },
        cache: "no-store",
      });
      const text = await res.text();
      return new NextResponse(text, {
        status: res.status,
        headers: { "content-type": res.headers.get("content-type") || "application/json" },
      });
    } catch (err) {
      lastErr = err;
    }
  }
  return NextResponse.json(
    { detail: `proxy error: ${lastErr?.message || "unknown"}` },
    { status: 502 },
  );
}
