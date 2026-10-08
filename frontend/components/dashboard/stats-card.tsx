import React from "react";
import { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type StatColor = "brand" | "emerald" | "amber" | "rose" | "slate" | "cyan";

interface StatsCardProps {
  title: string;
  value: number | string;
  description?: string;
  icon: LucideIcon;
  color?: StatColor;
  isLoading?: boolean;
  /** Optional trend line, e.g. "+12% vs last week". */
  trend?: string;
}

const COLOR_MAP: Record<StatColor, { plate: string; glow: string }> = {
  brand: {
    plate:
      "border-brand-100 bg-brand-50 text-brand-600 dark:border-brand-900/50 dark:bg-brand-950/40 dark:text-brand-300",
    glow: "from-brand-500/10",
  },
  emerald: {
    plate:
      "border-emerald-100 bg-emerald-50 text-emerald-600 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300",
    glow: "from-emerald-500/10",
  },
  amber: {
    plate:
      "border-amber-100 bg-amber-50 text-amber-600 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300",
    glow: "from-amber-500/10",
  },
  rose: {
    plate:
      "border-rose-100 bg-rose-50 text-rose-600 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300",
    glow: "from-rose-500/10",
  },
  cyan: {
    plate:
      "border-cyan-100 bg-cyan-50 text-cyan-600 dark:border-cyan-900/50 dark:bg-cyan-950/40 dark:text-cyan-300",
    glow: "from-cyan-500/10",
  },
  slate: {
    plate: "border-line bg-surface-muted text-ink-muted",
    glow: "from-ink-subtle/10",
  },
};

export function StatsCard({
  title,
  value,
  description,
  icon: Icon,
  color = "brand",
  isLoading,
  trend,
}: StatsCardProps) {
  const palette = COLOR_MAP[color];

  return (
    <Card
      interactive
      className="group relative overflow-hidden"
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 -top-16 h-32 bg-gradient-to-b to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100",
          palette.glow
        )}
      />
      <div className="relative flex items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold uppercase tracking-wide text-ink-subtle">
            {title}
          </p>
          {isLoading ? (
            <Skeleton className="mt-2.5 h-8 w-16" />
          ) : (
            <p className="mt-2 text-[28px] font-bold leading-none tracking-tight tabular text-ink">
              {value}
            </p>
          )}
          {description && (
            <p className="mt-2 text-xs leading-snug text-ink-muted">{description}</p>
          )}
          {trend && (
            <p className="mt-1.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
              {trend}
            </p>
          )}
        </div>
        <span
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-transform duration-200 group-hover:scale-105 [&_svg]:size-5",
            palette.plate
          )}
        >
          <Icon />
        </span>
      </div>
    </Card>
  );
}
