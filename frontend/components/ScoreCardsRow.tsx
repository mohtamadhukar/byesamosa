"use client";

import ScoreCard from "./ScoreCard";
import { formatDate, formatTime } from "@/lib/utils";
import type { DashboardResponse } from "@/lib/types";

interface ScoreCardsRowProps {
  data: DashboardResponse;
}

export default function ScoreCardsRow({ data }: ScoreCardsRowProps) {
  const { latest, deltas, insight } = data;

  const bedtimeSubtitle =
    latest.sleep.bedtime_start && latest.sleep.bedtime_end
      ? `${formatTime(latest.sleep.bedtime_start)} – ${formatTime(latest.sleep.bedtime_end)}`
      : undefined;

  const daySubtitle = formatDate(latest.day);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <ScoreCard
        label="Sleep Score"
        subtitle={bedtimeSubtitle}
        score={latest.sleep.score}
        delta={deltas.sleep_delta}
        contributors={latest.sleep.contributors}
        insight={insight?.score_insights?.sleep}
        benchmark={insight?.good_looks_like?.sleep}
        delay={0}
      />
      <ScoreCard
        label="Readiness Score"
        subtitle={daySubtitle}
        score={latest.readiness?.score ?? null}
        delta={deltas.readiness_delta}
        contributors={latest.readiness?.contributors ?? null}
        insight={insight?.score_insights?.readiness}
        benchmark={insight?.good_looks_like?.readiness}
        delay={0.1}
      />
      <ScoreCard
        label="Activity Score"
        subtitle={daySubtitle}
        score={latest.activity?.score ?? null}
        delta={deltas.activity_delta}
        contributors={latest.activity?.contributors ?? null}
        insight={insight?.score_insights?.activity}
        benchmark={insight?.good_looks_like?.activity}
        delay={0.2}
      />
    </div>
  );
}
