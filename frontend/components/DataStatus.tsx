"use client";

import { useState } from "react";
import { formatDate } from "@/lib/utils";
import type { DataStatusResponse } from "@/lib/types";
import PullButton from "./PullButton";

interface DataStatusProps {
  data: DataStatusResponse | null;
  onPullComplete: () => void;
}

export default function DataStatus({ data, onPullComplete }: DataStatusProps) {
  const [expanded, setExpanded] = useState(false);

  if (!data) return null;

  const { processed_range, raw_exports } = data;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-warm-200/50 p-5 mb-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-warm-900">Data Pipeline</h2>
          {processed_range && (
            <p className="text-sm text-warm-800/60 mt-0.5">
              Processed data:{" "}
              <span className="font-medium text-warm-800/80">
                {formatDate(processed_range.earliest)} &ndash;{" "}
                {formatDate(processed_range.latest)}
              </span>
            </p>
          )}
        </div>
        <PullButton onComplete={onPullComplete} />
      </div>

      {raw_exports.length > 0 && (
        <div className="mt-3 pt-3 border-t border-warm-200/50">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-warm-800/60 hover:text-warm-800 transition-colors flex items-center gap-1"
          >
            <span
              className="inline-block transition-transform duration-200"
              style={{ transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}
            >
              ▸
            </span>
            {raw_exports.length} raw export{raw_exports.length !== 1 ? "s" : ""}
          </button>
          {expanded && (
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {raw_exports.map((exp) => (
                <div
                  key={exp.date}
                  className="text-sm bg-warm-50 rounded-lg px-3 py-2 border border-warm-200/30"
                >
                  <span className="font-medium text-warm-800">
                    {formatDate(exp.date)}
                  </span>
                  <span className="text-warm-800/50 ml-1.5">
                    {exp.file_count} file{exp.file_count !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
