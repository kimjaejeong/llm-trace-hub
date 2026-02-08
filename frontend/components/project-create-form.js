"use client";

import { useState } from "react";

export default function ProjectCreateForm() {
  const [name, setName] = useState("");
  const [created, setCreated] = useState(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/admin/projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCreated(data);
      setName("");
      window.location.reload();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h3 className="subhead">Create Project</h3>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="project name" />
        <button className="button" type="submit" disabled={loading}>Create</button>
      </form>
      {created ? (
        <div style={{ marginTop: 10 }}>
          <p className="subtitle">New API key (save now):</p>
          <div className="code">{created.api_key}</div>
        </div>
      ) : null}
    </div>
  );
}
