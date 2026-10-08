import { cn } from "@/lib/utils";

/**
 * Determinate progress bar (uploads, extraction completeness).
 *
 * The fill is scaled from the left edge rather than having its `width`
 * animated, so the transition stays on the compositor and never triggers
 * layout. Origin is left, so the bar grows in the reading direction.
 */
export function Progress({
  value,
  className,
  tone = "brand",
}: {
  value: number;
  className?: string;
  tone?: "brand" | "emerald" | "rose";
}) {
  const clamped = Math.min(100, Math.max(0, value));
  const fill =
    tone === "emerald"
      ? "bg-emerald-500"
      : tone === "rose"
      ? "bg-rose-500"
      : "bg-brand-600";

  return (
    <div
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-surface-muted", className)}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn(
          "h-full w-full origin-left rounded-full transition-transform duration-500 ease-[var(--ease-settle)]",
          fill
        )}
        style={{ transform: `scale3d(${clamped / 100}, 1, 1)` }}
      />
    </div>
  );
}

/** Indeterminate bar for "we don't know how long this takes" states. */
export function IndeterminateProgress({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative h-1.5 w-full overflow-hidden rounded-full bg-surface-muted",
        className
      )}
      role="progressbar"
      aria-label="Working"
    >
      <div className="absolute inset-y-0 w-1/3 animate-progress rounded-full bg-brand-500 motion-essential" />
    </div>
  );
}
