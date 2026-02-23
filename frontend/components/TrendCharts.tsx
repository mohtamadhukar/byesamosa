"use client";

import AnimatedCard from "./AnimatedCard";
import SleepScoreTrend from "./SleepScoreTrend";
import HrvRhrTrend from "./HrvRhrTrend";
import type { TrendsResponse, BaselinePoint, AIInsight } from "@/lib/types";

interface TrendChartsProps {
  trends: TrendsResponse;
  baselines: BaselinePoint[];
  insight: AIInsight | null;
}

function TrendIcon({ icon }: { icon: string }) {
  if (icon === "up") return <span>📈</span>;
  if (icon === "down") return <span>📉</span>;
  return <span>❤️</span>;
}

export default function TrendCharts({
  trends,
  baselines,
  insight,
}: TrendChartsProps) {
  return (
    <AnimatedCard delay={0.25}>
      <h2 className="text-2xl font-bold text-warm-900 mb-6">
        Trends (30 days)
      </h2>
      <div className="space-y-8">
        <div>
          <SleepScoreTrend trend={trends.sleep_score} baselines={baselines} />
          {insight?.trend_annotations?.sleep_score && (
            <p className="mt-2 text-sm text-warm-800/70">
              <TrendIcon icon={insight.trend_annotations.sleep_score.icon} />{" "}
              {insight.trend_annotations.sleep_score.text}
            </p>
          )}
        </div>
        <div>
          <HrvRhrTrend
            hrvTrend={trends.average_hrv}
            rhrTrend={trends.lowest_heart_rate}
          />
          {insight?.trend_annotations?.hrv_rhr && (
            <p className="mt-2 text-sm text-warm-800/70">
              <TrendIcon icon={insight.trend_annotations.hrv_rhr.icon} />{" "}
              {insight.trend_annotations.hrv_rhr.text}
            </p>
          )}
        </div>
      </div>
    </AnimatedCard>
  );
}
