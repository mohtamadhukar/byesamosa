"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { triggerPull, fetchPullStatus } from "@/lib/api";

interface PullButtonProps {
  onComplete: () => void;
}

export default function PullButton({ onComplete }: PullButtonProps) {
  const [status, setStatus] = useState<
    "idle" | "running" | "completed" | "failed" | "requested"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetchPullStatus();
        if (res.status === "completed") {
          stopPolling();
          // Check if the output indicates an export was requested (not downloaded)
          if (res.output?.includes("Export has been requested")) {
            setStatus("requested");
            setMessage("Export requested — check back in ~48 hours");
            setTimeout(() => {
              setStatus("idle");
              setMessage(null);
            }, 8000);
          } else {
            setStatus("completed");
            onComplete();
            setTimeout(() => setStatus("idle"), 3000);
          }
        } else if (res.status === "failed") {
          stopPolling();
          setError("Pull failed. Check server logs.");
          setTimeout(() => {
            setStatus("idle");
            setError(null);
          }, 5000);
        } else {
          setStatus(res.status);
        }
      } catch {
        stopPolling();
        setStatus("idle");
        setError("Lost connection to server");
      }
    }, 2000);
  }, [stopPolling, onComplete]);

  useEffect(() => {
    return stopPolling;
  }, [stopPolling]);

  // Check if a pull is already running on mount
  useEffect(() => {
    fetchPullStatus().then((res) => {
      if (res.status === "running") {
        setStatus("running");
        startPolling();
      }
    }).catch(() => {});
  }, [startPolling]);

  const handleClick = useCallback(async () => {
    if (status === "running") return;
    setError(null);
    setMessage(null);
    try {
      await triggerPull();
      setStatus("running");
      startPolling();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start pull");
    }
  }, [status, startPolling]);

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={status === "running"}
        className="px-4 py-2 rounded-lg text-sm font-medium transition-colors
          bg-warm-800 text-white hover:bg-warm-900
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {status === "running" ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Pulling...
          </span>
        ) : status === "completed" ? (
          "Done!"
        ) : status === "requested" ? (
          "Requested"
        ) : (
          "Pull Data"
        )}
      </button>
      {message && <p className="text-xs text-warm-800/60">{message}</p>}
      {error && <p className="text-xs text-terracotta">{error}</p>}
    </div>
  );
}
