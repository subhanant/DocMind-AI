"use client";

import React from "react";
import Link from "next/link";
import { FileText, UploadCloud } from "lucide-react";
import { DocumentSummary } from "@/types";
import { DocumentTable } from "@/components/documents/document-table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

interface RecentDocumentsTableProps {
  documents: DocumentSummary[];
  isLoading?: boolean;
  onDelete?: (doc: DocumentSummary) => void;
  pendingDeleteId?: string | null;
}

export function RecentDocumentsTable({
  documents,
  isLoading,
  onDelete,
  pendingDeleteId,
}: RecentDocumentsTableProps) {
  return (
    <DocumentTable
      documents={documents}
      isLoading={isLoading}
      skeletonRows={5}
      pendingDeleteId={pendingDeleteId}
      onDelete={onDelete}
      emptyState={
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload a Bill of Lading, commercial invoice or packing list and DocMind AI will extract every field automatically."
          action={
            <Link href="/upload">
              <Button size="sm">
                <UploadCloud className="h-4 w-4" />
                Upload your first document
              </Button>
            </Link>
          }
        />
      }
    />
  );
}
