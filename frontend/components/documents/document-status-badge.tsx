import React from "react";
import { Badge } from "@/components/ui/badge";
import { DocumentStatus } from "@/types";
import { CheckCircle2, Clock, Loader2, AlertCircle, HelpCircle } from "lucide-react";

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="success" className="gap-1 py-0.5">
          <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          Completed
        </Badge>
      );
    case "processing":
      return (
        <Badge variant="default" className="gap-1 py-0.5">
          <Loader2 className="w-3 h-3 animate-spin text-blue-600 dark:text-blue-400" />
          Processing
        </Badge>
      );
    case "queued":
      return (
        <Badge variant="secondary" className="gap-1 py-0.5">
          <Clock className="w-3 h-3 text-slate-500" />
          Queued
        </Badge>
      );
    case "uploaded":
      return (
        <Badge variant="outline" className="gap-1 py-0.5 text-slate-600 dark:text-slate-400">
          <Clock className="w-3 h-3 text-slate-400" />
          Uploaded
        </Badge>
      );
    case "needs_review":
      return (
        <Badge variant="warning" className="gap-1 py-0.5">
          <AlertCircle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
          Needs Review
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive" className="gap-1 py-0.5">
          <AlertCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="gap-1 py-0.5">
          <HelpCircle className="w-3 h-3" />
          {status}
        </Badge>
      );
  }
}
