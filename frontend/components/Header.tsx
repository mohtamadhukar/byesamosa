"use client";

import { formatDate } from "@/lib/utils";
import RefreshButton from "./RefreshButton";

interface HeaderProps {
  day: string;
  onRefresh: () => Promise<void>;
}

export default function Header({ day, onRefresh }: HeaderProps) {
  return (
    <header className="flex items-end justify-between mb-8">
      <div>
        <h1 className="text-5xl font-bold tracking-tight text-warm-900">
          ByeSamosa
        </h1>
        <p className="mt-1 text-warm-800/60 text-lg">
          Data as of <span className="font-medium">{formatDate(day)}</span>
        </p>
      </div>
      <RefreshButton onRefresh={onRefresh} />
    </header>
  );
}
