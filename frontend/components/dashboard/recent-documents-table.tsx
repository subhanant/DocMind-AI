"use client";

import React from "react";
import Link from "next/link";
import {
  FileText,
  ExternalLink,
  Trash2,
  FileSpreadsheet,
  FileCode,
  FileCheck,
} from "lucide-react";
import { DocumentItem } from "@/types";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { formatBytes, formatConfidence, formatDocType, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface RecentDocumentsTableProps {
  documents: DocumentItem[];
  isLoading?: boolean;
  onDelete?: (id: string) => void;
}

export function RecentDocumentsTable({
  documents,
  isLoading,
  onDelete,
}: RecentDocumentsTableProps) {
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

  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs text-slate-400">
        <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-blue-600 border-r-transparent mb-2" />
        <p>Loading documents...</p>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="py-12 text-center">
        <FileText className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          No documents yet
        </h4>
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1 mb-4">
          Upload your bills of lading, commercial invoices, or other shipping documents to get started.
        </p>
        <Link href="/upload">
          <Button size="sm">Upload First Document</Button>
        </Link>
      </div>
    );
  }

  return (
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
              className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group"
            >
              <td className="px-5 py-3.5">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
                    {getFileIcon(doc.file_type)}
                  </div>
                  <div className="min-w-0 max-w-[200px] sm:max-w-xs">
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
                      className="h-7 px-2 text-xs text-slate-600 dark:text-slate-300 hover:text-blue-600"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1" />
                      View
                    </Button>
                  </Link>
                  {onDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(doc.id)}
                      className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
                      title="Delete document"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
