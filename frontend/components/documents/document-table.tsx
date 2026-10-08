"use client";

import React from "react";
import Link from "next/link";
import { Download, Eye, Trash2 } from "lucide-react";
import { DocumentSummary } from "@/types";
import { api } from "@/lib/api";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { FileTypeIcon } from "@/components/documents/file-icon";
import { Button } from "@/components/ui/button";
import { Table, TableWrapper, Td, Th, Tr } from "@/components/ui/table";
import { ConfidenceMeter } from "@/components/ui/confidence";
import { TableSkeleton } from "@/components/ui/skeleton";
import { cn, formatBytes, formatDate, formatDateTime, formatDocType } from "@/lib/utils";
import { motionVars } from "@/components/motion/reveal";

interface DocumentTableProps {
  documents: DocumentSummary[];
  isLoading?: boolean;
  onDelete?: (doc: DocumentSummary) => void;
  emptyState?: React.ReactNode;
  skeletonRows?: number;
  /** Highlights the row currently being deleted. */
  pendingDeleteId?: string | null;
  className?: string;
}

export function DocumentTable({
  documents,
  isLoading,
  onDelete,
  emptyState,
  skeletonRows = 5,
  pendingDeleteId,
  className,
}: DocumentTableProps) {
  if (isLoading) {
    return <TableSkeleton rows={skeletonRows} columns={6} />;
  }

  if (documents.length === 0) {
    return <>{emptyState}</>;
  }

  return (
    <TableWrapper className={className}>
      <Table>
        <caption className="sr-only">
          Processed documents with type, status and extraction confidence
        </caption>
        <thead>
          <tr>
            <Th>Document</Th>
            <Th className="hidden lg:table-cell">Type</Th>
            <Th className="hidden sm:table-cell">Status</Th>
            <Th className="hidden md:table-cell">Confidence</Th>
            <Th className="hidden xl:table-cell">Uploaded</Th>
            <Th className="text-right">Actions</Th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc, rowIndex) => (
            /* Opacity-only entrance: rows never move, so the table cannot jump.
               The animation is dropped while a row is pending deletion — an
               animation would otherwise override the `opacity-50` dimming. */
            <Tr
              key={doc.id}
              className={cn(
                "group",
                pendingDeleteId === doc.id ? "opacity-50" : "motion-fade"
              )}
              style={motionVars({ index: Math.min(rowIndex, 7), duration: "0.4s" })}
            >
              <Td className="max-w-[280px]">
                <div className="flex items-center gap-3">
                  <FileTypeIcon fileType={doc.file_type} />
                  <div className="min-w-0">
                    <Link
                      href={`/documents/${doc.id}`}
                      className="focus-ring block truncate rounded text-sm font-semibold text-ink transition-colors hover:text-brand-600 dark:hover:text-brand-300"
                      title={doc.original_filename}
                    >
                      {doc.original_filename}
                    </Link>
                    <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-ink-subtle">
                      <span className="tabular">{formatBytes(doc.file_size)}</span>
                      <span aria-hidden>·</span>
                      <span className="uppercase">{doc.file_type || "file"}</span>
                      <span className="sm:hidden">
                        <span aria-hidden> · </span>
                        <span
                          className={cn(
                            "font-medium capitalize",
                            doc.processing_status === "failed"
                              ? "text-rose-600 dark:text-rose-400"
                              : doc.processing_status === "completed"
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-ink-muted"
                          )}
                        >
                          {doc.processing_status.replace("_", " ")}
                        </span>
                      </span>
                    </p>
                  </div>
                </div>
              </Td>

              <Td className="hidden lg:table-cell">
                <span className="inline-flex rounded-lg border border-line bg-surface-muted px-2 py-0.5 text-[11px] font-medium text-ink-muted">
                  {formatDocType(doc.document_type)}
                </span>
              </Td>

              <Td className="hidden sm:table-cell">
                <DocumentStatusBadge status={doc.processing_status} />
              </Td>

              <Td className="hidden md:table-cell">
                {doc.extraction_confidence !== null &&
                doc.extraction_confidence !== undefined ? (
                  <ConfidenceMeter score={doc.extraction_confidence} />
                ) : (
                  <span className="text-xs text-ink-subtle">—</span>
                )}
              </Td>

              <Td className="hidden xl:table-cell">
                <time
                  dateTime={doc.uploaded_at}
                  title={formatDateTime(doc.uploaded_at)}
                  className="text-xs text-ink-muted"
                >
                  {formatDate(doc.uploaded_at)}
                </time>
              </Td>

              <Td className="text-right">
                <div className="flex items-center justify-end gap-1">
                  <Link href={`/documents/${doc.id}`} aria-label={`Open ${doc.original_filename}`}>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="View extraction"
                      className="text-ink-subtle hover:text-brand-600 dark:hover:text-brand-300"
                    >
                      <Eye />
                    </Button>
                  </Link>
                  <a
                    href={api.documents.getFileUrl(doc.id)}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Download ${doc.original_filename}`}
                  >
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="Download original file"
                      className="text-ink-subtle hover:text-ink"
                    >
                      <Download />
                    </Button>
                  </a>
                  {onDelete && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onDelete(doc)}
                      title="Delete document"
                      aria-label={`Delete ${doc.original_filename}`}
                      className="text-ink-subtle hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                    >
                      <Trash2 />
                    </Button>
                  )}
                </div>
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </TableWrapper>
  );
}
