"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type ConfidenceLevel = "high" | "medium" | "low";

export function confidenceLevel(score: number | null | undefined): ConfidenceLevel {
  const value = typeof score === "number" ? score : 0;
  if (value >= 0.8) return "high";
  if (value >= 0.6) return "medium";
  return "low";
}

const LEVEL_STYLES: Record<
  ConfidenceLevel,
  { bar: string; chip: string; label: string }
> = {
  high: {
    bar: "bg-emerald-500",
    chip: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/50 dark:text-emerald-300",
    label: "High confidence",
  },
  medium: {
    bar: "bg-amber-500",
    chip: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-300",
    label: "Medium confidence",
  },
  low: {
    bar: "bg-rose-500",
    chip: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/50 dark:text-rose-300",
    label: "Low confidence",
  },
};

export function confidencePercent(score: number | null | undefined): number {
  if (typeof score !== "number" || Number.isNaN(score)) return 0;
  return Math.round(Math.min(1, Math.max(0, score)) * 100);
}

/** Compact chip: percentage + colour-coded level. */
export function ConfidenceBadge({
  score,
  className,
  showIcon = false,
}: {
  score: number | null | undefined;
  className?: string;
  showIcon?: boolean;
}) {
  const level = confidenceLevel(score);
  const styles = LEVEL_STYLES[level];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold tabular",
        styles.chip,
        className
      )}
      title={styles.label}
    >
      {showIcon && (
        <span className={cn("h-1.5 w-1.5 rounded-full", styles.bar)} aria-hidden />
      )}
      {confidencePercent(score)}%
    </span>
  );
}

/** Chip + inline meter, used in dense tables. */
export function ConfidenceMeter({
  score,
  className,
  showValue = true,
}: {
  score: number | null | undefined;
  className?: string;
  showValue?: boolean;
}) {
  const level = confidenceLevel(score);
  const percent = confidencePercent(score);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-1.5 w-14 overflow-hidden rounded-full bg-surface-muted"
        role="meter"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Extraction confidence"
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-500", LEVEL_STYLES[level].bar)}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showValue && (
        <span className="text-xs font-medium tabular text-ink">{percent}%</span>
      )}
    </div>
  );
}

/** Circular gauge for overview headers. */
export function ConfidenceRing({
  score,
  size = 76,
  label = "Confidence",
}: {
  score: number | null | undefined;
  size?: number;
  label?: string;
}) {
  const percent = confidencePercent(score);
  const level = confidenceLevel(score);
  const stroke = size >= 72 ? 7 : 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  const strokeColor =
    level === "high"
      ? "stroke-emerald-500"
      : level === "medium"
      ? "stroke-amber-500"
      : "stroke-rose-500";

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label}: ${percent}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="stroke-surface-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={cn(strokeColor, "transition-[stroke-dashoffset] duration-700")}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-base font-bold tabular leading-none text-ink">{percent}%</span>
        <span className="mt-1 text-[9px] font-medium uppercase tracking-wider text-ink-subtle">
          {label}
        </span>
      </div>
    </div>
  );
}
