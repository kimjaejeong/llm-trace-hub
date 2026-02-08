"use client";

import { useState } from "react";

export default function ProjectAdminActions({ projectId, isActive }) {
  const [loading, setLoading] = useState(false);
  const [newKey, setNewKey] = useState("");

  async function call(path, method = "POST", confirmText = "", opts = {}) {
    if (confirmText && !window.confirm(confirmText)) return;
    setLoading(true);
    try {
      const res = await fetch(path, { method });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "request failed");
      if (data?.api_key) setNewKey(data.api_key);
      if (opts.reload) {
        window.location.reload();
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button
          className="button detail-btn"
          disabled={loading}
          onClick={() => call(`/api/admin/projects/${projectId}/rotate-key`)}
        >
          Rotate Key
        </button>
        {isActive ? (
          <button
            className="button detail-btn"
            disabled={loading}
            onClick={() => call(`/api/admin/projects/${projectId}/deactivate`, "POST", "", { reload: true })}
          >
            Deactivate
          </button>
        ) : (
          <button
            className="button detail-btn"
            disabled={loading}
            onClick={() => call(`/api/admin/projects/${projectId}/activate`, "POST", "", { reload: true })}
          >
            Activate
          </button>
        )}
        <button
          className="button detail-btn"
          disabled={loading}
          onClick={() =>
            call(
              `/api/admin/projects/${projectId}`,
              "DELETE",
              "프로젝트를 비활성화(삭제 처리)하시겠습니까?",
              { reload: true },
            )
          }
        >
          Delete
        </button>
      </div>
      {newKey ? (
        <div>
          <div className="subtitle">New API key</div>
          <div className="code">{newKey}</div>
        </div>
      ) : null}
    </div>
  );
}
