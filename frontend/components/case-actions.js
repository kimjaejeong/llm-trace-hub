"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const base = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const apiKey = process.env.NEXT_PUBLIC_API_KEY || "dev-key";

export default function CaseActions({ caseId, projectId }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [assignee, setAssignee] = useState("oncall");

  async function call(action) {
    setLoading(true);
    try {
      const res = await fetch(`${base}/api/v1/cases/${caseId}/${action}`, {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "content-type": "application/json",
          ...(projectId ? { "x-project-id": projectId } : {}),
        },
        body: JSON.stringify({ assignee }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      router.refresh();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <input className="input" value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="assignee" />
      <button className="button" disabled={loading} onClick={() => call("ack")}>Ack</button>
      <button className="button" disabled={loading} onClick={() => call("resolve")}>Resolve</button>
    </div>
  );
}
