"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import AnimatedCard from "./AnimatedCard";
import { ACTIVITY_COLORS } from "@/lib/constants";
import { formatDate, formatDateLabel } from "@/lib/utils";
import type { WorkoutRecoveryResponse } from "@/lib/types";

interface WorkoutRecoveryProps {
  data: WorkoutRecoveryResponse;
}

export default function WorkoutRecovery({ data }: WorkoutRecoveryProps) {
  if (!data.workouts.length) return null;

  // Build merged data: for each unique day, sum calories by activity type + readiness
  const dayMap = new Map<string, Record<string, number>>();

  // Seed all days from readiness
  for (const r of data.readiness) {
    if (!dayMap.has(r.day)) dayMap.set(r.day, {});
    dayMap.get(r.day)!._readiness = r.readiness;
  }

  // Add workout calories by activity type
  for (const w of data.workouts) {
    if (!dayMap.has(w.day)) dayMap.set(w.day, {});
    const entry = dayMap.get(w.day)!;
    entry[w.activity] = (entry[w.activity] || 0) + w.calories;
  }

  const chartData = Array.from(dayMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, vals]) => ({ day, ...vals }));

  const colorMap: Record<string, string> = {};
  data.activity_types.forEach((t, i) => {
    colorMap[t] = ACTIVITY_COLORS[i % ACTIVITY_COLORS.length];
  });

  return (
    <AnimatedCard delay={0.2}>
      <h2 className="text-2xl font-bold text-warm-900 mb-6">
        Workout & Recovery
      </h2>
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData}>
          <XAxis
            dataKey="day"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: "#44403C" }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: "#44403C" }}
            label={{
              value: "Calories",
              angle: -90,
              position: "insideLeft",
              style: { fontSize: 11, fill: "#44403C" },
            }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "#44403C" }}
            label={{
              value: "Readiness",
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
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            iconType="square"
          />
          {data.activity_types.map((activity) => (
            <Bar
              key={activity}
              dataKey={activity}
              yAxisId="left"
              stackId="workouts"
              fill={colorMap[activity]}
              radius={[2, 2, 0, 0]}
            />
          ))}
          <Line
            dataKey="_readiness"
            yAxisId="right"
            name="Readiness"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ r: 2, fill: "#22c55e" }}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="mt-3 text-xs text-warm-800/50">
        Readiness shows the full recovery arc — dips after workouts and how many
        days to recover.
        {data.excluded_count > 0 &&
          ` ${data.excluded_count} workout(s) excluded due to missing calorie data.`}
      </p>
    </AnimatedCard>
  );
}
