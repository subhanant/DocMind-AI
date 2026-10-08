import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Clock,
  Loader2,
  Upload,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DocumentStatus } from "@/types";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<
  DocumentStatus,
  {
    label: string;
    variant: "success" | "default" | "neutral" | "outline" | "warning" | "destructive";
    icon: React.ElementType;
    iconClass: string;
    pulse?: boolean;
  }
> = {
  completed: {
    label: "Completed",
    variant: "success",
    icon: CheckCircle2,
    iconClass: "text-emerald-600 dark:text-emerald-400",
  },
  processing: {
    label: "Processing",
    variant: "default",
    icon: Loader2,
    iconClass: "animate-spin text-brand-600 dark:text-brand-300",
  },
  queued: {
    label: "Queued",
    variant: "neutral",
    icon: Clock,
    iconClass: "text-ink-subtle",
  },
  uploaded: {
    label: "Uploaded",
    variant: "outline",
    icon: Upload,
    iconClass: "text-ink-subtle",
  },
  needs_review: {
    label: "Needs Review",
    variant: "warning",
    icon: AlertTriangle,
    iconClass: "text-amber-600 dark:text-amber-400",
  },
  failed: {
    label: "Failed",
    variant: "destructive",
    icon: AlertTriangle,
    iconClass: "text-rose-600 dark:text-rose-400",
  },
};

export function DocumentStatusBadge({
  status,
  className,
}: {
  status: DocumentStatus;
  className?: string;
}) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    variant: "outline" as const,
    icon: CircleHelp,
    iconClass: "text-ink-subtle",
  };
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn("py-0.5", className)}>
      <Icon className={cn("h-3 w-3", config.iconClass)} aria-hidden />
      {config.label}
    </Badge>
  );
}

/** Small dot-only indicator for dense views (tables, list rows). */
export function StatusDot({ status }: { status: DocumentStatus }) {
  const color =
    status === "completed"
      ? "bg-emerald-500"
      : status === "failed"
      ? "bg-rose-500"
      : status === "needs_review"
      ? "bg-amber-500"
      : status === "processing"
      ? "bg-brand-500"
      : "bg-ink-subtle";

  return (
    <span className="relative flex h-2 w-2 shrink-0" title={status}>
      {status === "processing" && (
        <span
          className={cn("absolute inline-flex h-full w-full animate-ring rounded-full", color)}
        />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", color)} />
    </span>
  );
}
