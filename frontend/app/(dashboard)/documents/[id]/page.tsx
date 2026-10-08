"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Columns,
  Download,
  Eye,
  ExternalLink,
  FileWarning,
  Layers,
  Maximize2,
  Sparkles,
  Trash2,
} from "lucide-react";
import { DocumentItem, ExtractionResult } from "@/types";
import { api } from "@/lib/api";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { ExtractionView } from "@/components/documents/extraction-view";
import { FileTypeIcon } from "@/components/documents/file-icon";
import { PipelineAudit } from "@/components/documents/pipeline-audit";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { useConfirm } from "@/components/ui/confirm-dialog";
import {
  cn,
  formatBytes,
  formatDateTime,
  formatDate,
  formatDocType,
} from "@/lib/utils";
import { MaskReveal, motionVars } from "@/components/motion/reveal";
import { ProcessingStrip } from "@/components/motion/processing-strip";

const IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"];

function DocumentPreview({
  doc,
  fileUrl,
  height = "h-[720px]",
}: {
  doc: DocumentItem;
  fileUrl: string;
  height?: string;
}) {
  const fileType = (doc.file_type ?? "").toLowerCase();

  return (
    <div className={cn("w-full bg-surface-muted", height)}>
      {fileType === "pdf" ? (
        <iframe
          src={`${fileUrl}#toolbar=0`}
          className="h-full w-full border-none"
          title={`Preview of ${doc.original_filename}`}
        />
      ) : IMAGE_TYPES.includes(fileType) ? (
        <div className="flex h-full w-full items-center justify-center overflow-auto p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={fileUrl}
            alt={doc.original_filename}
            className="max-h-full max-w-full rounded-lg object-contain shadow-lift"
          />
        </div>
      ) : (
        <div className="flex h-full flex-col items-center justify-center p-8 text-center">
          <FileWarning className="mb-3 h-12 w-12 text-ink-subtle" />
          <p className="text-sm font-medium text-ink">Preview unavailable</p>
          <p className="mt-1 text-xs text-ink-muted">
            {doc.file_type ? `.${doc.file_type}` : "This file type"} cannot be rendered inline.
          </p>
          <a href={fileUrl} download={doc.original_filename} className="mt-4">
            <Button size="sm" variant="outline">
              <Download className="h-3.5 w-3.5" />
              Download file
            </Button>
          </a>
        </div>
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-48" />
      <Card className="p-6">
        <div className="flex items-start gap-4">
          <Skeleton className="h-12 w-12 rounded-xl" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-56 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

export default function DocumentDetailsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const toast = useToast();
  const confirm = useConfirm();

  const [documentId, setDocumentId] = useState<string | null>(null);
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("extracted");
  const [sideBySide, setSideBySide] = useState(false);

  // Next 16 passes route params as a promise — unwrap once, then drive state from it.
  useEffect(() => {
    let active = true;
    params.then(({ id }) => {
      if (active) setDocumentId(id);
    });
    return () => {
      active = false;
    };
  }, [params]);

  const loadData = useCallback(
    async (id: string) => {
      try {
        setError(null);
        const [docData, extData] = await Promise.all([
          api.documents.get(id),
          api.documents.getExtraction(id),
        ]);
        setDoc(docData);
        setExtraction(extData);
      } catch {
        setError("This document could not be found or has been removed.");
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!documentId) return;
    const timeout = setTimeout(() => {
      setIsLoading(true);
      void loadData(documentId);
    }, 0);
    return () => clearTimeout(timeout);
  }, [documentId, loadData]);

  // Poll while the pipeline is still working on this document.
  useEffect(() => {
    if (!documentId || !doc) return;
    if (doc.processing_status !== "queued" && doc.processing_status !== "processing") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const [docData, extData] = await Promise.all([
          api.documents.get(documentId),
          api.documents.getExtraction(documentId),
        ]);
        setDoc(docData);
        if (extData && extData.extracted_json) setExtraction(extData);
      } catch {
        // Polling failures are transient; the next tick will retry.
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [doc, documentId]);

  const handleExtractionUpdated = async (newExt: ExtractionResult) => {
    setExtraction(newExt);
    if (!documentId) return;
    try {
      setDoc(await api.documents.get(documentId));
    } catch {
      setDoc((current) => (current ? { ...current, processing_status: "completed" } : null));
    }
  };

  const handleDelete = async () => {
    if (!doc) return;
    const confirmed = await confirm({
      title: "Delete this document?",
      description: `“${doc.original_filename}” and its extracted data will be permanently removed.`,
      confirmLabel: "Delete document",
      destructive: true,
    });
    if (!confirmed) return;

    try {
      await api.documents.delete(doc.id);
      toast.success("Document deleted", `"${doc.original_filename}" was removed.`);
      router.push("/documents");
    } catch {
      toast.error("Delete failed", "The document could not be removed.");
    }
  };

  if (isLoading || !documentId) {
    return <DetailSkeleton />;
  }

  if (error || !doc) {
    return (
      <Card className="mx-auto max-w-lg">
        <EmptyState
          tone="error"
          icon={FileWarning}
          title="Document not found"
          description={error ?? "The requested document does not exist or has been removed."}
          action={
            <Link href="/documents">
              <Button variant="outline" size="sm">
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to documents
              </Button>
            </Link>
          }
        />
      </Card>
    );
  }

  const fileUrl = api.documents.getFileUrl(doc.id);
  const isProcessing =
    doc.processing_status === "queued" || doc.processing_status === "processing";

  return (
    <div className="mx-auto max-w-[1400px] space-y-6 pb-10">
      {/* Top bar */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 motion-fade"
        style={motionVars({ duration: "0.5s" })}
      >
        <Link
          href="/documents"
          className="focus-ring inline-flex items-center gap-1.5 rounded-lg text-xs font-semibold text-ink-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to documents
        </Link>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSideBySide((value) => !value)}
            className="gap-1.5"
          >
            <Columns className="h-3.5 w-3.5 text-brand-500" />
            {sideBySide ? "Single view" : "Side-by-side"}
          </Button>
          <a href={fileUrl} target="_blank" rel="noreferrer">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Download
            </Button>
          </a>
          <Button variant="destructive" size="sm" onClick={handleDelete} className="gap-1.5">
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>

      {/* Header */}
      <Card
        className="overflow-hidden motion-settle"
        style={motionVars({ index: 0 })}
      >
        <div className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
          <div className="flex min-w-0 items-start gap-4">
            <FileTypeIcon fileType={doc.file_type} className="h-12 w-12 [&_svg]:size-6" />
            <div className="min-w-0">
              <MaskReveal
                as="h1"
                className="text-lg font-bold tracking-tight text-ink"
                delay={120}
              >
                <span className="break-words">{doc.original_filename}</span>
              </MaskReveal>
              <div className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-ink-muted">
                <span className="rounded-md border border-line bg-surface-muted px-2 py-0.5 font-semibold text-ink">
                  {formatDocType(doc.document_type)}
                </span>
                <span className="tabular">{formatBytes(doc.file_size)}</span>
                <span aria-hidden>·</span>
                <time dateTime={doc.uploaded_at} title={formatDateTime(doc.uploaded_at)}>
                  Uploaded {formatDate(doc.uploaded_at)}
                </time>
                {doc.processed_at && (
                  <>
                    <span aria-hidden>·</span>
                    <time dateTime={doc.processed_at} title={formatDateTime(doc.processed_at)}>
                      Processed {formatDate(doc.processed_at)}
                    </time>
                  </>
                )}
              </div>
            </div>
          </div>

          <DocumentStatusBadge status={doc.processing_status} />
        </div>

        {isProcessing && (
          <div className="border-t border-line bg-brand-50/60 dark:bg-brand-950/30">
            <ProcessingStrip className="h-0.5 rounded-none bg-brand-100 dark:bg-brand-950" />
            <div className="flex items-center gap-2.5 px-5 py-3 text-xs text-brand-800 dark:text-brand-200">
              <Sparkles className="h-4 w-4 shrink-0 animate-pulse motion-essential" />
              The AI pipeline is working on this document. Results refresh automatically.
            </div>
          </div>
        )}
      </Card>

      {/* Content */}
      {sideBySide ? (
        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
          <Card className="overflow-hidden xl:sticky xl:top-24">
            <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-muted/60 px-5 py-3">
              <span className="flex items-center gap-2 text-xs font-semibold text-ink">
                <Eye className="h-3.5 w-3.5 text-brand-500" />
                Original document
              </span>
              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="focus-ring inline-flex items-center gap-1 rounded text-[11px] font-semibold text-brand-600 hover:underline dark:text-brand-300"
              >
                Open in new tab
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <DocumentPreview doc={doc} fileUrl={fileUrl} />
          </Card>

          <div>
            <ExtractionView
              extraction={extraction}
              documentId={doc.id}
              documentType={doc.document_type}
              onExtractionUpdated={handleExtractionUpdated}
            />
          </div>
        </div>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} name="document-detail">
          <TabsList aria-label="Document views" className="w-full sm:w-auto">
            <TabsTrigger value="extracted" className="flex-1 sm:flex-none">
              <Sparkles className="h-3.5 w-3.5" />
              Extracted data
            </TabsTrigger>
            <TabsTrigger value="source" className="flex-1 sm:flex-none">
              <Eye className="h-3.5 w-3.5" />
              Document
            </TabsTrigger>
            <TabsTrigger value="processing" className="flex-1 sm:flex-none">
              <Layers className="h-3.5 w-3.5" />
              Pipeline audit
            </TabsTrigger>
          </TabsList>

          <TabsContent value="extracted">
            <ExtractionView
              extraction={extraction}
              documentId={doc.id}
              documentType={doc.document_type}
              onExtractionUpdated={handleExtractionUpdated}
            />
          </TabsContent>

          <TabsContent value="source">
            <Card className="overflow-hidden">
              <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
                <span className="flex items-center gap-2 text-xs font-semibold text-ink">
                  <Eye className="h-3.5 w-3.5 text-brand-500" />
                  Original document
                </span>
                <a href={fileUrl} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <Maximize2 className="h-3.5 w-3.5" />
                    Open full size
                  </Button>
                </a>
              </div>
              <DocumentPreview doc={doc} fileUrl={fileUrl} />
            </Card>
          </TabsContent>

          <TabsContent value="processing">
            <PipelineAudit documentId={doc.id} extraction={extraction} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
