"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function tabClass(active) {
  return active ? "button" : "button subtle";
}

export default function ProjectTabs({ projectId }) {
  const pathname = usePathname() || "";
  const onCases = pathname.endsWith(`/projects/${projectId}/cases`);

  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <Link className="button subtle" href="/projects">Back To Projects</Link>
        <Link className={tabClass(!onCases)} href={`/projects/${projectId}`}>Trace Dashboard</Link>
        <Link className={tabClass(onCases)} href={`/projects/${projectId}/cases`}>Cases</Link>
        <span className="pill neutral">project_id: {projectId}</span>
      </div>
    </div>
  );
}
