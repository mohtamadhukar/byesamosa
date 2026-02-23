"use client";

import type { ActionItem } from "@/lib/types";

const PRIORITY_STYLES: Record<string, string> = {
  high: "border-l-terracotta bg-red-50/50",
  medium: "border-l-amber bg-amber-50/50",
  low: "border-l-sage bg-green-50/50",
};

interface ActionItemsProps {
  actions: ActionItem[];
}

export default function ActionItems({ actions }: ActionItemsProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-warm-900">Action Items</h3>
      {actions.map((action, i) => (
        <div
          key={i}
          className={`border-l-4 rounded-r-lg p-4 ${
            PRIORITY_STYLES[action.priority] || "border-l-gray-300"
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <p className="font-medium text-sm text-warm-900">{action.title}</p>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-warm-200/60 text-warm-800">
              {action.tag}
            </span>
          </div>
          <p className="text-sm text-warm-800/70 leading-relaxed">
            {action.detail}
          </p>
        </div>
      ))}
    </div>
  );
}
