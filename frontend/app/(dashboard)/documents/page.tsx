"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  UploadCloud,
  ChevronLeft,
  ChevronRight,
  Trash2,
  ExternalLink,
  Loader2,
  FileSpreadsheet,
  FileCode,
  FileCheck,
} from "lucide-react";
import { DocumentItem, DocumentStatus, DocumentType } from "@/types";
import { api } from "@/lib/api";
import { DocumentFilters } from "@/components/documents/document-filters";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { formatBytes, formatConfidence, formatDocType, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType | "">("");
  const [status, setStatus] = useState<DocumentStatus | "">("");

  const loadDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.documents.list({
        page,
        size: pageSize,
        search: search.trim() || undefined,
        document_type: documentType || undefined,
        status: status || undefined,
      });
      setDocuments(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch {
      setError("Could not load documents. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, documentType, status]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Reset page when filters change
  const handleSearchChange = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  const handleDocumentTypeChange = (val: DocumentType | "") => {
    setDocumentType(val);
    setPage(1);
  };

  const handleStatusChange = (val: DocumentStatus | "") => {
    setStatus(val);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSearch("");
    setDocumentType("");
    setStatus("");
    setPage(1);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await api.documents.delete(id);
      loadDocuments();
    } catch {
      alert("Failed to delete document.");
    }
  };

  const getFileIcon = (fileType: string | null | undefined) => {
    switch ((fileType ?? "").toLowerCase()) {
      case "pdf":
        return <FileText className="w-4 h-4 text-rose-500" />;
      case "xlsx":
      case "xls":
      case "csv":
        return <FileSpreadsheet className="w-4 h-4 text-emerald-500" />;
      case "docx":
      case "doc":
        return <FileCode className="w-4 h-4 text-blue-500" />;
      default:
        return <FileCheck className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Documents
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage, search, and inspect your processed shipping and trade documents.
          </p>
        </div>

        <Link href="/upload">
          <Button className="gap-2 shadow-sm">
            <UploadCloud className="w-4 h-4" />
            Upload Document
          </Button>
        </Link>
      </div>

      {/* Filters Bar */}
      <DocumentFilters
        search={search}
        onSearchChange={handleSearchChange}
        documentType={documentType}
        onDocumentTypeChange={handleDocumentTypeChange}
        status={status}
        onStatusChange={handleStatusChange}
        onReset={handleResetFilters}
      />

      {/* Table Card */}
      <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="py-20 text-center text-xs text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
            <p>Loading documents...</p>
          </div>
        ) : error ? (
          <div className="py-16 text-center">
            <FileText className="w-12 h-12 mx-auto text-rose-300 dark:text-rose-900 mb-3" />
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Documents could not be loaded
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 mb-4">
              {error}
            </p>
            <Button variant="outline" size="sm" onClick={loadDocuments}>
              Try Again
            </Button>
          </div>
        ) : documents.length === 0 ? (
          <div className="py-16 text-center">
            <FileText className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              No matching documents
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1 mb-4">
              {search || documentType || status
                ? "Try clearing your search or adjusting your filters to find what you need."
                : "No documents have been uploaded yet. Upload your first file to get started."}
            </p>
            {search || documentType || status ? (
              <Button variant="outline" size="sm" onClick={handleResetFilters}>
                Clear Filters
              </Button>
            ) : (
              <Link href="/upload">
                <Button size="sm">Upload Document</Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                <tr>
                  <th className="px-5 py-3">Filename</th>
                  <th className="px-4 py-3">Document Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Uploaded</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
                          {getFileIcon(doc.file_type)}
                        </div>
                        <div className="min-w-0 max-w-[220px] sm:max-w-xs md:max-w-md">
                          <Link
                            href={`/documents/${doc.id}`}
                            className="font-medium text-xs text-slate-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate block"
                            title={doc.original_filename}
                          >
                            {doc.original_filename}
                          </Link>
                          <span className="text-[11px] text-slate-400 block">
                            {formatBytes(doc.file_size)} • {(doc.file_type ?? "unknown").toUpperCase()}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {formatDocType(doc.document_type)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <DocumentStatusBadge status={doc.processing_status} />
                    </td>
                    <td className="px-4 py-3.5 text-xs font-medium text-slate-700 dark:text-slate-300">
                      {doc.extraction_confidence !== null ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-12 bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-emerald-500 h-full rounded-full"
                              style={{
                                width: `${Math.round(doc.extraction_confidence * 100)}%`,
                              }}
                            />
                          </div>
                          <span>{formatConfidence(doc.extraction_confidence)}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500 dark:text-slate-400">
                      {formatDate(doc.uploaded_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Link href={`/documents/${doc.id}`}>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2 text-xs text-slate-600 dark:text-slate-300 hover:text-blue-600"
                          >
                            <ExternalLink className="w-3.5 h-3.5 mr-1" />
                            Details
                          </Button>
                        </Link>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(doc.id, doc.original_filename)}
                          className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3.5 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 text-xs text-slate-500 dark:text-slate-400">
          <div>
            Showing <span className="font-semibold text-slate-900 dark:text-slate-100">{documents.length}</span> of{" "}
            <span className="font-semibold text-slate-900 dark:text-slate-100">{total}</span> documents
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || isLoading}
              className="h-8 px-2.5 text-xs gap-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Previous
            </Button>

            <span className="text-xs px-2">
              Page {page} of {Math.max(1, totalPages)}
            </span>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || isLoading}
              className="h-8 px-2.5 text-xs gap-1"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
