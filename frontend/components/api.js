const apiKey = process.env.API_KEY || process.env.NEXT_PUBLIC_API_KEY || "dev-key";

function baseCandidates() {
  const values = [
    process.env.BACKEND_URL,
    process.env.NEXT_PUBLIC_BACKEND_URL,
    "http://backend:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
  ];
  return values.filter(Boolean);
}

export async function fetchApi(path) {
  let lastError = null;
  for (const base of baseCandidates()) {
    try {
      const res = await fetch(`${base}${path}`, {
        headers: { "x-api-key": apiKey },
        cache: "no-store",
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `failed ${path} via ${base}`);
      }
      return res.json();
    } catch (err) {
      lastError = err;
    }
  }
  throw new Error(`fetch failed for ${path}: ${lastError?.message || "unknown error"}`);
}
