"use client";

import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";

interface RadarChartProps {
  contributors: Record<string, number | null>;
}

export default function RadarChart({ contributors }: RadarChartProps) {
  const data = Object.entries(contributors)
    .filter(([, v]) => v !== null)
    .map(([key, value]) => ({
      name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: value as number,
    }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RechartsRadar cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: "#44403C" }}
        />
        <Radar
          dataKey="value"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.15}
          strokeWidth={2}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}
