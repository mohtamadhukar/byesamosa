"use client";

import AnimatedCard from "./AnimatedCard";
import ReasoningChain from "./ReasoningChain";
import ActionItems from "./ActionItems";
import type { AIInsight } from "@/lib/types";

interface AIBriefingProps {
  insight: AIInsight;
}

export default function AIBriefing({ insight }: AIBriefingProps) {
  return (
    <AnimatedCard delay={0.1}>
      <h2 className="text-2xl font-bold text-warm-900 mb-6">AI Briefing</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <ReasoningChain steps={insight.reasoning_chain} />
        <ActionItems actions={insight.actions} />
      </div>
    </AnimatedCard>
  );
}
