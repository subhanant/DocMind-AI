"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { motionVars } from "@/components/motion/reveal";

interface PipelineHealthProps {
  total: number;
  completed: number;
  needsReview: number;
  failed: number;
  processing: number;
  isLoading?: boolean;
}

const SEGMENTS = [
  { key: "completed", label: "Completed", bar: "bg-emerald-500", dot: "bg-emerald-500" },
  { key: "processing", label: "In progress", bar: "bg-brand-500", dot: "bg-brand-500" },
  { key: "needsReview", label: "Needs review", bar: "bg-amber-500", dot: "bg-amber-500" },
  { key: "failed", label: "Failed", bar: "bg-rose-500", dot: "bg-rose-500" },
  { key: "queued", label: "Queued", bar: "bg-slate-400", dot: "bg-slate-400" },
] as const;

export function PipelineHealth({
  total,
  completed,
  needsReview,
  failed,
  processing,
  isLoading,
}: PipelineHealthProps) {
  const queued = Math.max(0, total - completed - needsReview - failed - processing);
  const values: Record<string, number> = {
    completed,
    processing,
    needsReview,
    failed,
    queued,
  };
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-sm">Pipeline health</CardTitle>
          {!isLoading && (
            <span className="text-lg font-bold tabular text-ink">{successRate}%</span>
          )}
        </div>
        <p className="text-xs text-ink-muted">
          Share of documents fully extracted and validated
        </p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-2.5 w-full rounded-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        ) : total === 0 ? (
          <p className="py-2 text-xs text-ink-muted">
            No documents processed yet. Upload one to see pipeline health.
          </p>
        ) : (
          <>
            <div
              className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full bg-surface-muted"
              role="img"
              aria-label={`${completed} completed, ${processing} in progress, ${needsReview} need review, ${failed} failed, ${queued} queued`}
            >
              {SEGMENTS.map((segment, segmentIndex) => {
                const value = values[segment.key];
                if (!value) return null;
                return (
                  /* DRAW: each segment grows from its own left edge. Width is
                     set once; only `transform` animates, so nothing reflows. */
                  <div
                    key={segment.key}
                    className={cn(
                      "h-full origin-left motion-draw-x first:rounded-l-full last:rounded-r-full",
                      segment.bar
                    )}
                    style={{
                      width: `${(value / total) * 100}%`,
                      ...motionVars({ index: segmentIndex, duration: "0.75s" }),
                    }}
                  />
                );
              })}
            </div>

            <ul className="mt-4 space-y-2">
              {SEGMENTS.map((segment, segmentIndex) => {
                const value = values[segment.key];
                if (!value) return null;
                return (
                  <li
                    key={segment.key}
                    className="flex items-center gap-2 text-xs motion-fade"
                    style={motionVars({ index: segmentIndex, delay: 220, duration: "0.4s" })}
                  >
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", segment.dot)} />
                    <span className="text-ink-muted">{segment.label}</span>
                    <span className="ml-auto font-semibold tabular text-ink">{value}</span>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
