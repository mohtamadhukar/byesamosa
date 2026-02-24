"use client";

import AnimatedCard from "./AnimatedCard";
import RadarChart from "./RadarChart";
import { scoreColor, formatDelta } from "@/lib/utils";
import type { ScoreInsight } from "@/lib/types";

interface ScoreCardProps {
  label: string;
  subtitle?: string;
  score: number | null;
  delta?: number;
  contributors: Record<string, number | null> | object | null;
  insight?: ScoreInsight;
  benchmark?: string;
  delay?: number;
}

export default function ScoreCard({
  label,
  subtitle,
  score,
  delta,
  contributors,
  insight,
  benchmark,
  delay = 0,
}: ScoreCardProps) {
  return (
    <AnimatedCard delay={delay}>
      <div className="text-center mb-3">
        <p className="text-sm font-medium text-warm-800/60 uppercase tracking-wide">
          {label}
        </p>
        {subtitle && (
          <p className="text-xs text-warm-800/40 mt-0.5">{subtitle}</p>
        )}
        <p
          className="text-5xl font-bold mt-1"
          style={{ color: scoreColor(score) }}
        >
          {score ?? "--"}
        </p>
        {delta !== undefined && (
          <span
            className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              delta >= 0
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-terracotta"
            }`}
          >
            {formatDelta(delta)}
          </span>
        )}
      </div>

      {contributors && (
        <RadarChart
          contributors={contributors as Record<string, number | null>}
        />
      )}

      {insight && (
        <p className="mt-3 text-sm text-warm-800/80 leading-relaxed">
          {insight.one_liner}
        </p>
      )}

      {benchmark && (
        <p className="mt-2 text-xs text-warm-800/50">
          <span className="font-medium">Good looks like:</span> {benchmark}
        </p>
      )}
    </AnimatedCard>
  );
}
