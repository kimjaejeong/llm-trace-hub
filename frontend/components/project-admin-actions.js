"use client";

import { useEffect, useState } from "react";

export default function ProjectAdminActions({ projectId, isActive }) {
  const [loading, setLoading] = useState(false);
  const [rotatedKey, setRotatedKey] = useState("");
  const [currentKey, setCurrentKey] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);

  useEffect(() => {
    if (!showCurrent) return undefined;
    const timer = setTimeout(() => setShowCurrent(false), 20000);
    return () => clearTimeout(timer);
  }, [showCurrent]);

  async function call(path, method = "POST", confirmText = "", opts = {}) {
    if (confirmText && !window.confirm(confirmText)) return;
    setLoading(true);
    try {
      const res = await fetch(path, { method });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "request failed");
      if (data?.api_key) {
        setRotatedKey(data.api_key);
        setShowCurrent(false);
      }
      if (opts.reload) {
        window.location.reload();
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function showCurrentKey() {
    if (showCurrent) {
      setShowCurrent(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/admin/projects/${projectId}/current-key`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "request failed");
      if (!data?.api_key) {
        alert("Current key is not available yet. Rotate Key once to initialize.");
        return;
      }
      setCurrentKey(data.api_key);
      setShowCurrent(true);
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
          onClick={showCurrentKey}
        >
          {showCurrent ? "Hide Key" : "Show Key"}
        </button>
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
      {rotatedKey ? (
        <div>
          <div className="subtitle">Rotated API key</div>
          <div className="code">{rotatedKey}</div>
        </div>
      ) : null}
      {showCurrent && currentKey ? (
        <div>
          <div className="subtitle">Current API key</div>
          <div className="code">{currentKey}</div>
        </div>
      ) : null}
    </div>
  );
}
