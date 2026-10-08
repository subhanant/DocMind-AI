"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Clock,
  Loader2,
  AlertCircle,
  UploadCloud,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { DashboardStats, DocumentItem } from "@/types";
import { api } from "@/lib/api";
import { StatsCard } from "@/components/dashboard/stats-card";
import { RecentDocumentsTable } from "@/components/dashboard/recent-documents-table";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const [statsData, docsData] = await Promise.all([
        api.dashboard.getStats(),
        api.dashboard.getRecentDocuments(5),
      ]);
      setStats(statsData);
      setRecentDocs(docsData);
    } catch {
      // Silently handle error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleDeleteDocument = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.documents.delete(id);
      loadDashboardData();
    } catch {
      alert("Failed to delete document.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Welcome back, {user?.full_name?.split(" ")[0] || "there"}
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Here is your document intelligence and processing summary.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/upload">
            <Button className="gap-2 shadow-sm">
              <UploadCloud className="w-4 h-4" />
              Upload Documents
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Documents"
          value={isLoading ? "—" : stats?.total_documents ?? 0}
          description="Stored in pipeline"
          icon={FileText}
          color="blue"
        />
        <StatsCard
          title="Processed Today"
          value={isLoading ? "—" : stats?.processed_today ?? 0}
          description="Completed in last 24h"
          icon={TrendingUp}
          color="emerald"
        />
        <StatsCard
          title="Processing"
          value={
            isLoading
              ? "—"
              : (stats?.processing ?? 0) + (stats?.total_documents ?? 0) - (stats?.completed ?? 0) - (stats?.failed ?? 0) - (stats?.needs_review ?? 0) > 0
              ? (stats?.processing ?? 0)
              : 0
          }
          description="In active queue"
          icon={Clock}
          color="amber"
        />
        <StatsCard
          title="Needs Review"
          value={isLoading ? "—" : stats?.needs_review ?? 0}
          description="Requires manual verification"
          icon={AlertCircle}
          color="rose"
        />
      </div>

      {/* Main Content: Recent Documents and Pipeline Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Documents Table (2 columns on lg) */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-4 px-5 border-b border-slate-100 dark:border-slate-800">
              <div>
                <CardTitle className="text-sm font-semibold">
                  Recent Documents
                </CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Latest uploaded bills of lading and trade records
                </p>
              </div>
              <Link
                href="/documents"
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
              >
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              <RecentDocumentsTable
                documents={recentDocs}
                isLoading={isLoading}
                onDelete={handleDeleteDocument}
              />
            </CardContent>
          </Card>
        </div>

        {/* Pipeline Readiness & Document Types Breakdown (1 column on lg) */}
        <div className="space-y-6">
          {/* Phase 1 Architecture Card */}
          <Card className="border-blue-100 dark:border-blue-900/40 bg-gradient-to-br from-blue-50/50 via-white to-white dark:from-blue-950/20 dark:via-slate-900 dark:to-slate-900">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Architecture Status
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  Phase 1 Live
                </span>
              </div>
              <CardTitle className="text-base font-bold mt-1">
                Document Processor
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-slate-600 dark:text-slate-300">
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="text-slate-900 dark:text-white">
                    Storage Service:
                  </strong>{" "}
                  Local storage abstraction ready for S3/MinIO.
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="text-slate-900 dark:text-white">
                    Bill of Lading Schema:
                  </strong>{" "}
                  Full standardized multi-entity fields configured.
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="text-slate-900 dark:text-white">
                    Inbox Integration DB:
                  </strong>{" "}
                  Gmail/Outlook tables with encrypted token storage.
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href="/upload" className="block">
                <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5">
                    <UploadCloud className="w-4 h-4 text-blue-600" />
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      Upload New Documents
                    </span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </Link>

              <Link href="/email-connections" className="block">
                <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      View Inbox Integrations
                    </span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
