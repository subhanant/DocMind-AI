"use client";

import React from "react";
import { RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { DocumentStatus, DocumentType } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

interface DocumentFiltersProps {
  search: string;
  onSearchChange: (val: string) => void;
  documentType: DocumentType | "";
  onDocumentTypeChange: (val: DocumentType | "") => void;
  status: DocumentStatus | "";
  onStatusChange: (val: DocumentStatus | "") => void;
  onReset: () => void;
  resultCount?: number;
  isLoading?: boolean;
}

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "commercial_invoice", label: "Commercial Invoice" },
  { value: "packing_list", label: "Packing List" },
  { value: "purchase_order", label: "Purchase Order" },
  { value: "certificate_of_origin", label: "Certificate of Origin" },
  { value: "delivery_challan", label: "Delivery Challan" },
  { value: "customs_document", label: "Customs Document" },
  { value: "shipping_document", label: "Shipping Document" },
  { value: "contract", label: "Contract" },
  { value: "receipt", label: "Receipt" },
  { value: "general_document", label: "General Document" },
];

const STATUSES: { value: DocumentStatus; label: string }[] = [
  { value: "uploaded", label: "Uploaded" },
  { value: "queued", label: "Queued" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "needs_review", label: "Needs Review" },
  { value: "failed", label: "Failed" },
];

export function DocumentFilters({
  search,
  onSearchChange,
  documentType,
  onDocumentTypeChange,
  status,
  onStatusChange,
  onReset,
  resultCount,
  isLoading,
}: DocumentFiltersProps) {
  const hasActiveFilters = Boolean(search || documentType || status);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card lg:flex-row lg:items-center">
      <div className="flex flex-1 items-center gap-2 lg:max-w-sm">
        <Input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search by filename or ID…"
          aria-label="Search documents"
          leadingIcon={<Search />}
          className="[&::-webkit-search-cancel-button]:hidden"
        />
      </div>

      <div className="flex flex-1 flex-wrap items-center gap-2">
        <div className="min-w-[160px] flex-1">
          <Select
            size="sm"
            aria-label="Filter by document type"
            value={documentType}
            onChange={(event) => onDocumentTypeChange(event.target.value as DocumentType | "")}
            placeholder="All document types"
            options={DOCUMENT_TYPES}
          />
        </div>

        <div className="min-w-[140px] flex-1">
          <Select
            size="sm"
            aria-label="Filter by status"
            value={status}
            onChange={(event) => onStatusChange(event.target.value as DocumentStatus | "")}
            placeholder="All statuses"
            options={STATUSES}
          />
        </div>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="text-ink-muted hover:text-ink"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2 border-t border-line pt-3 text-xs text-ink-subtle lg:border-0 lg:pt-0">
        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
        {isLoading ? (
          <span>Filtering…</span>
        ) : (
          <span className="tabular">
            {resultCount !== undefined
              ? `${resultCount} document${resultCount === 1 ? "" : "s"}`
              : "Filtered results"}
          </span>
        )}
      </div>
    </div>
  );
}
