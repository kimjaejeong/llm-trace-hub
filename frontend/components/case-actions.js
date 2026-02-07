"use client";

import { useState } from "react";

const base = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const apiKey = process.env.NEXT_PUBLIC_API_KEY || "dev-key";

export default function CaseActions({ caseId }) {
  const [loading, setLoading] = useState(false);

  async function call(action) {
    setLoading(true);
    try {
      const res = await fetch(`${base}/api/v1/cases/${caseId}/${action}`, {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "content-type": "application/json",
        },
        body: JSON.stringify({ assignee: "oncall" }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      window.location.reload();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8 }}>
      <button className="input" disabled={loading} onClick={() => call("ack")}>Ack</button>
      <button className="input" disabled={loading} onClick={() => call("resolve")}>Resolve</button>
    </div>
  );
}
