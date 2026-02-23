"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import { formatDate, formatDateLabel } from "@/lib/utils";
import type { TrendPoint } from "@/lib/types";

interface HrvRhrTrendProps {
  hrvTrend: TrendPoint[];
  rhrTrend: TrendPoint[];
}

export default function HrvRhrTrend({ hrvTrend, rhrTrend }: HrvRhrTrendProps) {
  if (!hrvTrend.length && !rhrTrend.length) return null;

  // Merge by day
  const dayMap = new Map<string, { hrv?: number; rhr?: number }>();
  for (const p of hrvTrend) {
    dayMap.set(p.day, { ...dayMap.get(p.day), hrv: p.value });
  }
  for (const p of rhrTrend) {
    dayMap.set(p.day, { ...dayMap.get(p.day), rhr: p.value });
  }

  const chartData = Array.from(dayMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, vals]) => ({ day, ...vals }));

  return (
    <div>
      <h3 className="text-lg font-semibold text-warm-900 mb-3">
        HRV + Resting Heart Rate
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <XAxis
            dataKey="day"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: "#44403C" }}
          />
          <YAxis
            yAxisId="hrv"
            tick={{ fontSize: 11, fill: "#44403C" }}
            label={{
              value: "HRV (ms)",
              angle: -90,
              position: "insideLeft",
              style: { fontSize: 11, fill: "#44403C" },
            }}
          />
          <YAxis
            yAxisId="rhr"
            orientation="right"
            tick={{ fontSize: 11, fill: "#44403C" }}
            label={{
              value: "RHR (bpm)",
              angle: 90,
              position: "insideRight",
              style: { fontSize: 11, fill: "#44403C" },
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#FDFBF7",
              border: "1px solid #F5E6CC",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={formatDateLabel}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            dataKey="hrv"
            yAxisId="hrv"
            name="HRV (ms)"
            stroke={CHART_COLORS.hrv}
            strokeWidth={2}
            dot={{ r: 3, fill: CHART_COLORS.hrv }}
            connectNulls
          />
          <Line
            dataKey="rhr"
            yAxisId="rhr"
            name="RHR (bpm)"
            stroke={CHART_COLORS.rhr}
            strokeWidth={2}
            dot={{ r: 3, fill: CHART_COLORS.rhr }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
