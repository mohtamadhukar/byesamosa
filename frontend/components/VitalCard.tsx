"use client";

interface VitalCardProps {
  label: string;
  value: string;
  annotation?: string;
}

export default function VitalCard({ label, value, annotation }: VitalCardProps) {
  return (
    <div className="text-center">
      <p className="text-xs font-medium text-warm-800/50 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-2xl font-bold text-warm-900 mt-1">{value}</p>
      {annotation && (
        <p className="mt-1 text-xs text-warm-800/60 leading-relaxed">
          {annotation}
        </p>
      )}
    </div>
  );
}
