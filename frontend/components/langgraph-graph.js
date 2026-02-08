"use client";

import { useState } from "react";

function nodeHref(traceId, nodeId) {
  return `/traces/${traceId}/nodes/${nodeId}`;
}

export default function LangGraphGraph({ traceId, topology }) {
  const [expanded, setExpanded] = useState(false);
  const markerId = `arrowhead-${String(traceId).replaceAll("-", "")}`;

  return (
    <div>
      <div className="graph-toolbar">
        <button className="button" type="button" onClick={() => setExpanded((prev) => !prev)}>
          {expanded ? "접기" : "크게 보기"}
        </button>
      </div>
      <div className={`graph-canvas-wrap ${expanded ? "expanded" : ""}`}>
        <svg className="graph-canvas" viewBox={`0 0 ${topology.width} ${topology.height}`} preserveAspectRatio="xMinYMin meet">
          <defs>
            <marker id={markerId} markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#8aa0b8" />
            </marker>
          </defs>
          {topology.edges.map((edge, idx) => (
            <line
              key={idx}
              x1={edge.fromX}
              y1={edge.fromY}
              x2={edge.toX}
              y2={edge.toY}
              stroke="#8aa0b8"
              strokeWidth="1.6"
              markerEnd={`url(#${markerId})`}
            />
          ))}
          {topology.nodes.map((node) => (
            <a key={node.id} href={nodeHref(traceId, node.id)}>
              <g>
                <rect
                  x={node.x}
                  y={node.y}
                  width={topology.boxW}
                  height={topology.boxH}
                  rx="12"
                  fill="#ffffff"
                  stroke="#cdd8e8"
                />
                <text x={node.x + 10} y={node.y + 24} fontSize="12" fontWeight="700" fill="#132742">
                  {(node.attributes?.node_name || node.name || "").slice(0, 25)}
                </text>
                <text x={node.x + 10} y={node.y + 42} fontSize="11" fill="#5f7188">
                  {(node.attributes?.node_type || "-").slice(0, 20)}
                </text>
                <text x={node.x + 10} y={node.y + 60} fontSize="11" fill="#5f7188">
                  {String(node.status).slice(0, 20)}
                </text>
              </g>
            </a>
          ))}
        </svg>
      </div>
    </div>
  );
}
