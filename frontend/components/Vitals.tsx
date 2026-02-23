"use client";

import AnimatedCard from "./AnimatedCard";
import VitalCard from "./VitalCard";
import type { DashboardResponse } from "@/lib/types";

interface VitalsProps {
  data: DashboardResponse;
}

export default function Vitals({ data }: VitalsProps) {
  const sleep = data.latest.sleep;
  const readiness = data.latest.readiness;
  const insight = data.insight;

  const hrv = sleep.average_hrv;
  const rhr = sleep.lowest_heart_rate;
  const temp = readiness?.temperature_deviation ?? sleep.temperature_deviation;
  const breath = sleep.average_breath;

  return (
    <AnimatedCard delay={0.15}>
      <h2 className="text-2xl font-bold text-warm-900 mb-6">Vitals</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <VitalCard
          label="HRV (avg)"
          value={hrv !== null ? `${hrv} ms` : "--"}
          annotation={insight?.vital_annotations?.hrv?.text}
        />
        <VitalCard
          label="Resting HR"
          value={rhr !== null ? `${rhr} bpm` : "--"}
          annotation={insight?.vital_annotations?.rhr?.text}
        />
        <VitalCard
          label="Body Temp"
          value={temp !== null && temp !== undefined ? `${temp > 0 ? "+" : ""}${temp.toFixed(1)} \u00b0C` : "--"}
          annotation={insight?.vital_annotations?.temp?.text}
        />
        <VitalCard
          label="Breathing Rate"
          value={breath !== null ? `${breath.toFixed(1)} /min` : "--"}
          annotation={insight?.vital_annotations?.breath?.text}
        />
      </div>
    </AnimatedCard>
  );
}
