const apiKey = process.env.API_KEY || process.env.NEXT_PUBLIC_API_KEY || "dev-key";
const adminKey = process.env.ADMIN_KEY || process.env.NEXT_PUBLIC_ADMIN_KEY || apiKey;

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

export async function fetchApi(path, options = {}) {
  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    for (const base of baseCandidates()) {
      try {
        const headers = {
          "x-api-key": options.useAdmin ? adminKey : apiKey,
          ...(options.headers || {}),
        };
        const res = await fetch(`${base}${path}`, {
          headers,
          cache: "no-store",
        });
        if (!res.ok) {
          const text = await res.text();
          // HTTP error should be returned as-is; don't hide it with fallback network errors.
          const err = new Error(text || `failed ${path} via ${base}`);
          err.name = "HttpError";
          throw err;
        }
        return res.json();
      } catch (err) {
        if (err?.name === "HttpError") {
          throw err;
        }
        lastError = err;
      }
    }
    if (attempt === 0) {
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`fetch failed for ${path}: ${lastError?.message || "unknown error"}`);
}
