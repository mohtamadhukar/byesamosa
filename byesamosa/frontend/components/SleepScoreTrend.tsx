"use client";

import {
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Line,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import { formatDate, formatDateLabel } from "@/lib/utils";
import type { TrendPoint, BaselinePoint } from "@/lib/types";

interface SleepScoreTrendProps {
  trend: TrendPoint[];
  baselines: BaselinePoint[];
}

export default function SleepScoreTrend({
  trend,
  baselines,
}: SleepScoreTrendProps) {
  if (!trend.length) return null;

  // Merge trend data with baselines
  const baselineMap = new Map(
    baselines.map((b) => [
      b.day,
      {
        avg: b.avg_30d,
        upper: b.avg_30d && b.std_30d ? b.avg_30d + b.std_30d : null,
        lower: b.avg_30d && b.std_30d ? b.avg_30d - b.std_30d : null,
      },
    ])
  );

  const chartData = trend.map((t) => {
    const bl = baselineMap.get(t.day);
    return {
      day: t.day,
      score: t.value,
      band: bl?.upper != null && bl?.lower != null ? [bl.lower, bl.upper] : null,
    };
  });

  return (
    <div>
      <h3 className="text-lg font-semibold text-warm-900 mb-3">Sleep Score</h3>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData}>
          <XAxis
            dataKey="day"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: "#44403C" }}
          />
          <YAxis
            domain={[40, 100]}
            tick={{ fontSize: 11, fill: "#44403C" }}
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
          <Area
            dataKey="band"
            stroke="none"
            fill={CHART_COLORS.baselineBand}
            name="30d avg +/- 1 sigma"
            legendType="line"
            tooltipType="none"
          />
          <Line
            dataKey="score"
            name="Sleep Score"
            stroke={CHART_COLORS.sleep}
            strokeWidth={2}
            dot={{ r: 3, fill: CHART_COLORS.sleep }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
