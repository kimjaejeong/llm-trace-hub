"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

const INTERVALS = [3000, 5000, 10000, 15000];

function formatTime(ts) {
  if (!ts) return "-";
  return new Date(ts).toLocaleTimeString();
}

export default function LiveRefreshShell({ label = "Live Stream", defaultLive = true }) {
  const router = useRouter();
  const [live, setLive] = useState(defaultLive);
  const [intervalMs, setIntervalMs] = useState(5000);
  const [lastUpdated, setLastUpdated] = useState(Date.now());
  const [isPending, startTransition] = useTransition();

  const status = useMemo(() => {
    if (!live) return "paused";
    if (isPending) return "syncing";
    return "live";
  }, [isPending, live]);

  useEffect(() => {
    if (!live) return undefined;
    const timer = setInterval(() => {
      if (isPending) return;
      startTransition(() => router.refresh());
      setLastUpdated(Date.now());
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, live, router, isPending]);

  return (
    <div className="live-shell">
      <div className="live-left">
        <div className={`live-dot ${status}`} />
        <div>
          <div className="live-title">{label}</div>
          <div className="live-meta">
            Status: <strong>{status}</strong> · Last update {formatTime(lastUpdated)}
          </div>
        </div>
      </div>
      <div className="live-controls">
        <button className="button subtle" type="button" onClick={() => setLive((prev) => !prev)}>
          {live ? "Pause" : "Resume"}
        </button>
        <select className="input compact" value={intervalMs} onChange={(e) => setIntervalMs(Number(e.target.value))}>
          {INTERVALS.map((ms) => (
            <option key={ms} value={ms}>
              {ms / 1000}s
            </option>
          ))}
        </select>
        <button
          className="button"
          type="button"
          onClick={() => {
            startTransition(() => router.refresh());
            setLastUpdated(Date.now());
          }}
        >
          Refresh now
        </button>
      </div>
    </div>
  );
}
