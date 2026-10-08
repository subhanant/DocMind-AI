"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, FileText, RotateCcw, UploadCloud } from "lucide-react";
import { DocumentItem, DocumentStatus, DocumentType } from "@/types";
import { api } from "@/lib/api";
import { DocumentFilters } from "@/components/documents/document-filters";
import { DocumentTable } from "@/components/documents/document-table";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { Reveal, motionVars } from "@/components/motion/reveal";

const PAGE_SIZE = 10;

export default function DocumentsPage() {
  const toast = useToast();
  const confirm = useConfirm();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType | "">("");
  const [status, setStatus] = useState<DocumentStatus | "">("");

  const loadDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.documents.list({
        page,
        size: PAGE_SIZE,
        search: search.trim() || undefined,
        document_type: documentType || undefined,
        status: status || undefined,
      });
      setDocuments(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch {
      setError("The document list could not be loaded. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [page, search, documentType, status]);

  // Debounced so typing in the search box doesn't fire a request per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadDocuments();
    }, 250);
    return () => clearTimeout(timeout);
  }, [loadDocuments]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleDocumentTypeChange = (value: DocumentType | "") => {
    setDocumentType(value);
    setPage(1);
  };

  const handleStatusChange = (value: DocumentStatus | "") => {
    setStatus(value);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSearch("");
    setDocumentType("");
    setStatus("");
    setPage(1);
  };

  const handleDelete = async (doc: { id: string; original_filename: string }) => {
    const confirmed = await confirm({
      title: "Delete this document?",
      description: `“${doc.original_filename}” and its extracted data will be permanently removed.`,
      confirmLabel: "Delete document",
      destructive: true,
    });
    if (!confirmed) return;

    setPendingDeleteId(doc.id);
    try {
      await api.documents.delete(doc.id);
      toast.success("Document deleted", `"${doc.original_filename}" was removed.`);
      await loadDocuments();
    } catch {
      toast.error("Delete failed", "The document could not be removed.");
    } finally {
      setPendingDeleteId(null);
    }
  };

  const hasActiveFilters = Boolean(search || documentType || status);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Documents"
        description="Search, filter and inspect every document in your pipeline, with extraction confidence at a glance."
        actions={
          <Link href="/upload">
            <Button className="gap-2">
              <UploadCloud className="h-4 w-4" />
              Upload document
            </Button>
          </Link>
        }
      />

      <Reveal index={0} duration="0.6s">
        <DocumentFilters
          search={search}
          onSearchChange={handleSearchChange}
          documentType={documentType}
          onDocumentTypeChange={handleDocumentTypeChange}
          status={status}
          onStatusChange={handleStatusChange}
          onReset={handleResetFilters}
          resultCount={total}
          isLoading={isLoading}
        />
      </Reveal>

      <Card
        className="overflow-hidden motion-settle"
        style={motionVars({ index: 1 })}
      >
        {error ? (
          <EmptyState
            tone="error"
            icon={AlertTriangle}
            title="Documents could not be loaded"
            description={error}
            action={
              <Button variant="outline" size="sm" onClick={() => loadDocuments()}>
                <RotateCcw className="h-3.5 w-3.5" />
                Try again
              </Button>
            }
          />
        ) : (
          <>
            <DocumentTable
              documents={documents}
              isLoading={isLoading}
              skeletonRows={PAGE_SIZE}
              pendingDeleteId={pendingDeleteId}
              onDelete={handleDelete}
              emptyState={
                <EmptyState
                  icon={FileText}
                  title={
                    hasActiveFilters ? "No matching documents" : "No documents yet"
                  }
                  description={
                    hasActiveFilters
                      ? "Try clearing your search or adjusting the filters to find what you need."
                      : "Upload your first Bill of Lading or invoice and DocMind AI will extract every field automatically."
                  }
                  action={
                    hasActiveFilters ? (
                      <Button variant="outline" size="sm" onClick={handleResetFilters}>
                        <RotateCcw className="h-3.5 w-3.5" />
                        Clear filters
                      </Button>
                    ) : (
                      <Link href="/upload">
                        <Button size="sm">
                          <UploadCloud className="h-4 w-4" />
                          Upload document
                        </Button>
                      </Link>
                    )
                  }
                />
              }
            />

            {total > 0 && (
              <Pagination
                page={page}
                totalPages={totalPages}
                total={total}
                pageSize={PAGE_SIZE}
                isLoading={isLoading}
                onPageChange={setPage}
                label="documents"
              />
            )}
          </>
        )}
      </Card>
    </div>
  );
}
