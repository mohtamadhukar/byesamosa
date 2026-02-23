"use client";

import { useState, useEffect, useCallback } from "react";

interface RefreshButtonProps {
  onRefresh: () => Promise<void>;
}

export default function RefreshButton({ onRefresh }: RefreshButtonProps) {
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const handleClick = useCallback(async () => {
    if (loading || cooldown > 0) return;
    setLoading(true);
    setError(null);
    try {
      await onRefresh();
      setCooldown(60);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to refresh");
    } finally {
      setLoading(false);
    }
  }, [loading, cooldown, onRefresh]);

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={loading || cooldown > 0}
        className="px-4 py-2 rounded-lg text-sm font-medium transition-colors
          bg-amber text-white hover:bg-amber-light
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Generating...
          </span>
        ) : cooldown > 0 ? (
          `Wait ${cooldown}s`
        ) : (
          "Refresh Insights (~$0.05)"
        )}
      </button>
      {error && <p className="text-xs text-terracotta">{error}</p>}
    </div>
  );
}
