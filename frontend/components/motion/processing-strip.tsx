import { cn } from "@/lib/utils";

/*
 * Processing indicator for the upload/extraction pipeline.
 *
 * Two modes, both transform-based (never `width`):
 *   • determinate  — a fill scaled from the left edge, easing toward each new
 *                    value so a jumpy 0→40→70 sequence reads as one motion
 *   • indeterminate — a short bar sweeps across a hairline track
 *
 * The sweep is the only continuously-running animation in the app and it is
 * mounted only while a document is genuinely processing.
 */

interface ProcessingStripProps {
  /** 0–100. Omit for an indeterminate sweep. */
  progress?: number;
  className?: string;
  tone?: "brand" | "muted";
}

export function ProcessingStrip({
  progress,
  className,
  tone = "brand",
}: ProcessingStripProps) {
  const hasProgress = typeof progress === "number";
  const clamped = hasProgress ? Math.min(100, Math.max(0, progress)) : 0;

  return (
    <div
      className={cn(
        "relative h-px w-full overflow-hidden rounded-full",
        tone === "brand" ? "bg-brand-100 dark:bg-brand-950" : "bg-line",
        className
      )}
      role={hasProgress ? "progressbar" : undefined}
      aria-valuenow={hasProgress ? Math.round(clamped) : undefined}
      aria-valuemin={hasProgress ? 0 : undefined}
      aria-valuemax={hasProgress ? 100 : undefined}
    >
      {hasProgress ? (
        <span
          className={cn(
            "absolute inset-0 origin-left rounded-full",
            tone === "brand" ? "bg-brand-500" : "bg-ink-subtle",
            "transition-transform duration-500 ease-[var(--ease-settle)]"
          )}
          style={{ transform: `scale3d(${clamped / 100}, 1, 1)` }}
        />
      ) : (
        <span
          className={cn(
            "absolute inset-y-0 left-0 w-1/4 rounded-full motion-sweep motion-essential",
            "bg-gradient-to-r from-transparent via-brand-500 to-transparent"
          )}
        />
      )}
    </div>
  );
}
