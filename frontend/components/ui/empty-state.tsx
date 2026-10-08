import * as React from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ElementType;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  /** Visual treatment for failed states (rose icon plate instead of neutral). */
  tone?: "neutral" | "error";
  className?: string;
  compact?: boolean;
}

/**
 * Shared empty / zero-data / error placeholder so every surface in the app
 * communicates the same way.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = "neutral",
  className,
  compact,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center px-6 text-center",
        compact ? "py-10" : "py-14",
        className
      )}
    >
      {Icon && (
        <div
          className={cn(
            "mb-4 flex items-center justify-center rounded-2xl border",
            compact ? "h-11 w-11" : "h-14 w-14",
            tone === "error"
              ? "border-rose-200 bg-rose-50 text-rose-500 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400"
              : "border-line bg-surface-muted text-ink-subtle"
          )}
        >
          <Icon className={compact ? "h-5 w-5" : "h-6 w-6"} aria-hidden />
        </div>
      )}
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-ink-muted">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
