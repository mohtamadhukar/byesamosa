"use client";

import type { ReasoningStep } from "@/lib/types";

const ICONS: Record<string, string> = {
  Observation: "\uD83D\uDD0D",
  Cause: "\uD83E\uDDE0",
  "So what": "\u26A1",
};

interface ReasoningChainProps {
  steps: ReasoningStep[];
}

export default function ReasoningChain({ steps }: ReasoningChainProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-warm-900">Reasoning Chain</h3>
      {steps.map((step, i) => (
        <div key={i} className="flex gap-3">
          <span className="text-xl shrink-0">
            {ICONS[step.label] || "\u2022"}
          </span>
          <div>
            <p className="font-medium text-sm text-warm-900">{step.label}</p>
            <p className="text-sm text-warm-800/80 leading-relaxed">
              {step.text}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
