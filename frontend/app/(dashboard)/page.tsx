"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Clock3,
  Cpu,
  FileText,
  RefreshCw,
  Sparkles,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import { DashboardStats, DocumentSummary, RecentDocument } from "@/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { StatsCard } from "@/components/dashboard/stats-card";
import { RecentDocumentsTable } from "@/components/dashboard/recent-documents-table";
import { PipelineHealth } from "@/components/dashboard/pipeline-health";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { useToast } from "@/components/ui/toast";
import { useConfirm } from "@/components/ui/confirm-dialog";

function toSummary(doc: RecentDocument): DocumentSummary {
  const extension = doc.original_filename.includes(".")
    ? doc.original_filename.split(".").pop() ?? null
    : null;
  return {
    id: doc.id,
    original_filename: doc.original_filename,
    file_type: extension,
    file_size: doc.file_size,
    document_type: doc.document_type,
    processing_status: doc.processing_status,
    extraction_confidence: doc.extraction_confidence,
    uploaded_at: doc.uploaded_at,
  };
}

export default function DashboardPage() {
  const { user } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const loadDashboardData = useCallback(async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);
      const [statsData, docsData] = await Promise.all([
        api.dashboard.getStats(),
        api.dashboard.getRecentDocuments(5),
      ]);
      setStats(statsData);
      setRecentDocs(docsData.map(toSummary));
    } catch {
      setError(
        "We could not reach the processing service. Check that the backend is running and refresh."
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => void loadDashboardData(), 0);
    return () => clearTimeout(timeout);
  }, [loadDashboardData]);

  const handleDeleteDocument = async (id: string, name: string) => {
    const confirmed = await confirm({
      title: "Delete this document?",
      description: `“${name}” and its extracted data will be permanently removed. This cannot be undone.`,
      confirmLabel: "Delete document",
      destructive: true,
    });
    if (!confirmed) return;

    setPendingDeleteId(id);
    try {
      await api.documents.delete(id);
      toast.success("Document deleted", `"${name}" was removed from your workspace.`);
      await loadDashboardData(true);
    } catch {
      toast.error("Delete failed", "The document could not be removed. Please try again.");
    } finally {
      setPendingDeleteId(null);
    }
  };

  const firstName = user?.full_name?.split(" ")[0] || "there";
  const inProgress = stats?.currently_processing ?? 0;

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-line bg-surface shadow-card">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_120%_at_100%_0%,color-mix(in_oklab,var(--color-brand-500)_14%,transparent),transparent_55%)]"
        />
        <div
          aria-hidden
          className="grid-pattern pointer-events-none absolute inset-0 text-brand-500 opacity-40 [mask-image:radial-gradient(80%_60%_at_100%_0%,black,transparent)]"
        />

        <div className="relative flex flex-col gap-6 p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-2.5 py-1 text-[11px] font-semibold text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/50 dark:text-brand-300">
              <Sparkles className="h-3 w-3" />
              AI extraction engine online
            </span>
            <h1 className="mt-4 text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              Welcome back, {firstName}
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-muted">
              Upload trade documents and DocMind AI classifies them, runs OCR and returns
              structured, confidence-scored fields in seconds.
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-2.5">
              <Link href="/upload">
                <Button size="lg" className="gap-2">
                  <UploadCloud className="h-4 w-4" />
                  Upload documents
                </Button>
              </Link>
              <Link href="/documents">
                <Button size="lg" variant="outline" className="gap-2">
                  Browse documents
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Pipeline visual */}
          <div className="w-full shrink-0 lg:w-[300px]">
            <div className="rounded-2xl border border-line bg-surface-muted/70 p-4 backdrop-blur">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
                <Cpu className="h-3.5 w-3.5" />
                Processing pipeline
              </div>
              <ol className="mt-3 space-y-2.5">
                {[
                  { label: "Text & OCR extraction", detail: "PyMuPDF + OCR fallback" },
                  { label: "Document classification", detail: "Schema routing" },
                  { label: "Structured field extraction", detail: "Confidence scored" },
                  { label: "Validation & review routing", detail: "Threshold checks" },
                ].map((stage, index) => (
                  <li key={stage.label} className="flex items-start gap-2.5">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-brand-600 text-[10px] font-bold text-white">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-ink">{stage.label}</p>
                      <p className="text-[11px] text-ink-subtle">{stage.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <Alert
          variant="error"
          title="Unable to load dashboard data"
          action={
            <Button size="sm" variant="outline" onClick={() => loadDashboardData()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard
          title="Total documents"
          value={isLoading ? "—" : (stats?.total_documents ?? 0)}
          description="Stored in your workspace"
          icon={FileText}
          color="brand"
          isLoading={isLoading}
        />
        <StatsCard
          title="Processed today"
          value={isLoading ? "—" : (stats?.processed_today ?? 0)}
          description="Completed since midnight"
          icon={TrendingUp}
          color="emerald"
          isLoading={isLoading}
        />
        <StatsCard
          title="In progress"
          value={isLoading ? "—" : inProgress}
          description="Queued for extraction"
          icon={Clock3}
          color="cyan"
          isLoading={isLoading}
        />
        <StatsCard
          title="Needs review"
          value={isLoading ? "—" : (stats?.needs_review ?? 0)}
          description="Below confidence threshold"
          icon={AlertTriangle}
          color="amber"
          isLoading={isLoading}
        />
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="overflow-hidden xl:col-span-2">
          <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-ink">Recent documents</h2>
              <p className="mt-0.5 text-xs text-ink-subtle">
                The latest uploads in your workspace
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => loadDashboardData(true)}
                disabled={isRefreshing}
                aria-label="Refresh recent documents"
                title="Refresh"
                className="text-ink-subtle hover:text-ink"
              >
                <RefreshCw className={isRefreshing ? "animate-spin" : undefined} />
              </Button>
              <Link
                href="/documents"
                className="focus-ring inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-brand-600 transition-colors hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-950/40"
              >
                View all
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
          <RecentDocumentsTable
            documents={recentDocs}
            isLoading={isLoading}
            pendingDeleteId={pendingDeleteId}
            onDelete={(doc) =>
              handleDeleteDocument(doc.id, doc.original_filename)
            }
          />
        </Card>

        <div className="space-y-6">
          <PipelineHealth
            total={stats?.total_documents ?? 0}
            completed={stats?.total_completed ?? 0}
            needsReview={stats?.needs_review ?? 0}
            failed={stats?.total_failed ?? 0}
            processing={stats?.currently_processing ?? 0}
            isLoading={isLoading}
          />

          <Card>
            <div className="border-b border-line px-5 py-4">
              <h2 className="text-sm font-semibold text-ink">Quick actions</h2>
              <p className="mt-0.5 text-xs text-ink-subtle">
                Common tasks in your workspace
              </p>
            </div>
            <div className="space-y-2 p-4">
              {[
                {
                  href: "/upload",
                  icon: UploadCloud,
                  title: "Upload new documents",
                  description: "Batch upload up to 10 files",
                  tone: "text-brand-600 dark:text-brand-300 bg-brand-50 dark:bg-brand-950/50",
                },
                {
                  href: "/documents",
                  icon: FileText,
                  title: "Review extractions",
                  description: "Inspect and correct extracted fields",
                  tone: "text-emerald-600 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/50",
                },
                {
                  href: "/email-connections",
                  icon: Sparkles,
                  title: "Inbox automations",
                  description: "Connect Gmail or Outlook",
                  tone: "text-cyan-600 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/50",
                },
              ].map((action) => (
                <Link
                  key={action.href + action.title}
                  href={action.href}
                  className="focus-ring group flex items-center gap-3 rounded-xl border border-line p-3 transition-[border-color,background-color,transform] duration-150 hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-hover"
                >
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg [&_svg]:size-4 ${action.tone}`}
                  >
                    <action.icon />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-ink">
                      {action.title}
                    </span>
                    <span className="block truncate text-[11px] text-ink-subtle">
                      {action.description}
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-ink-subtle transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-ink" />
                </Link>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
