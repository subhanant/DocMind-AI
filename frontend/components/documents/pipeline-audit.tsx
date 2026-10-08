"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Circle,
  Clock,
  Cpu,
  FileText,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { ExtractionResult, ProcessingStageStatus, ProcessingStatus } from "@/types";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const STAGE_CONFIG: Record<
  ProcessingStageStatus,
  { icon: React.ElementType; iconClass: string; chip: string; label: string }
> = {
  completed: {
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    chip: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/50 dark:text-emerald-300",
    label: "Completed",
  },
  in_progress: {
    icon: Loader2,
    iconClass: "animate-spin text-brand-500",
    chip: "border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/50 dark:text-brand-300",
    label: "In progress",
  },
  pending: {
    icon: Circle,
    iconClass: "text-ink-subtle",
    chip: "border-line bg-surface-muted text-ink-subtle",
    label: "Pending",
  },
  failed: {
    icon: AlertTriangle,
    iconClass: "text-rose-500",
    chip: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/50 dark:text-rose-300",
    label: "Failed",
  },
};

function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function PipelineAudit({
  documentId,
  extraction,
}: {
  documentId: string;
  extraction: ExtractionResult | null;
}) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = React.useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setStatus(await api.documents.getProcessingStatus(documentId));
    } catch {
      setError("Processing stages could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    const timeout = setTimeout(() => void load(), 0);
    return () => clearTimeout(timeout);
  }, [load]);

  const metadata = (extraction?.processing_metadata ?? {}) as Record<string, unknown>;
  const facts: Array<{ label: string; value: string }> = [
    { label: "Pages processed", value: String(metadata.pages_processed ?? "—") },
    { label: "OCR used", value: metadata.ocr_used ? "Yes" : "No" },
    {
      label: "Duration",
      value:
        typeof metadata.processing_duration === "number"
          ? `${metadata.processing_duration.toFixed(2)}s`
          : "—",
    },
    { label: "Model", value: String(metadata.model_name ?? "—") },
    {
      label: "Extraction version",
      value: String(extraction?.schema_version ?? metadata.extraction_version ?? "—"),
    },
    {
      label: "Fields edited",
      value: String(extraction?.edit_history?.length ?? 0),
    },
  ];

  return (
    <div className="space-y-5">
      {error && (
        <Alert
          variant="error"
          title="Audit unavailable"
          action={
            <Button size="sm" variant="outline" onClick={() => load()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="flex items-center gap-2.5">
            <Activity className="h-4 w-4 text-brand-500" aria-hidden />
            <div>
              <h2 className="text-sm font-semibold text-ink">Pipeline execution</h2>
              <p className="mt-0.5 text-xs text-ink-subtle">
                Live stage status reported by the processing service
              </p>
            </div>
          </div>
          {status && (
            <span className="rounded-lg bg-surface-muted px-2 py-1 text-xs font-semibold tabular text-ink">
              {status.progress_percentage}%
            </span>
          )}
        </div>

        <div className="p-5">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : status ? (
            <>
              <Progress value={status.progress_percentage} className="mb-5" />

              {status.error_message && (
                <Alert variant="error" title="Pipeline error" className="mb-4">
                  {status.error_message}
                </Alert>
              )}

              <ol className="space-y-3">
                {status.stages.map((stage, index) => {
                  const config = STAGE_CONFIG[stage.status] ?? STAGE_CONFIG.pending;
                  const Icon = config.icon;
                  return (
                    <li
                      key={`${stage.name}-${index}`}
                      className="flex items-start gap-3 rounded-xl border border-line bg-surface-muted/50 p-4"
                    >
                      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", config.iconClass)} />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-ink">
                            {stage.name}
                          </p>
                          <span
                            className={cn(
                              "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                              config.chip
                            )}
                          >
                            {config.label}
                          </span>
                        </div>
                        {stage.message && (
                          <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                            {stage.message}
                          </p>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>

              <div className="mt-5 flex items-center gap-2 text-xs text-ink-subtle">
                <Clock className="h-3.5 w-3.5" />
                Current stage:{" "}
                <span className="font-semibold text-ink">
                  {titleCase(status.current_stage || "unknown")}
                </span>
                <span aria-hidden>·</span>
                <span>Overall: {titleCase(status.overall_status)}</span>
              </div>
            </>
          ) : (
            <p className="py-6 text-center text-xs text-ink-muted">
              No stage information is available for this document yet.
            </p>
          )}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-2.5 border-b border-line px-5 py-4">
          <Cpu className="h-4 w-4 text-cyan-500" aria-hidden />
          <h2 className="text-sm font-semibold text-ink">Run metadata</h2>
        </div>
        <dl className="grid grid-cols-2 gap-px bg-line sm:grid-cols-3">
          {facts.map((fact) => (
            <div key={fact.label} className="bg-surface px-5 py-4">
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
                {fact.label}
              </dt>
              <dd className="mt-1 truncate text-sm font-semibold text-ink" title={fact.value}>
                {fact.value}
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      {extraction?.edit_history && extraction.edit_history.length > 0 && (
        <Card className="overflow-hidden">
          <div className="flex items-center gap-2.5 border-b border-line px-5 py-4">
            <FileText className="h-4 w-4 text-amber-500" aria-hidden />
            <h2 className="text-sm font-semibold text-ink">
              Edit history
              <span className="ml-1.5 text-ink-subtle">
                ({extraction.edit_history.length})
              </span>
            </h2>
          </div>
          <ul className="divide-y divide-line">
            {extraction.edit_history
              .slice()
              .reverse()
              .map((entry, index) => (
                <li key={index} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 px-5 py-3 text-xs">
                  <span className="font-mono font-semibold text-ink">
                    {String(entry.field_path ?? "field")}
                  </span>
                  <span className="text-ink-subtle">
                    {String(entry.original_value ?? "—")}
                  </span>
                  <span aria-hidden className="text-ink-subtle">
                    →
                  </span>
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                    {String(entry.edited_value ?? "—")}
                  </span>
                  {entry.edited_at && (
                    <time className="ml-auto text-[11px] text-ink-subtle">
                      {new Date(String(entry.edited_at)).toLocaleString()}
                    </time>
                  )}
                </li>
              ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
