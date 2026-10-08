"use client";

import React from "react";
import { Search, X, Filter } from "lucide-react";
import { DocumentStatus, DocumentType } from "@/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface DocumentFiltersProps {
  search: string;
  onSearchChange: (val: string) => void;
  documentType: DocumentType | "";
  onDocumentTypeChange: (val: DocumentType | "") => void;
  status: DocumentStatus | "";
  onStatusChange: (val: DocumentStatus | "") => void;
  onReset: () => void;
}

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "commercial_invoice", label: "Commercial Invoice" },
  { value: "packing_list", label: "Packing List" },
  { value: "purchase_order", label: "Purchase Order" },
  { value: "certificate_of_origin", label: "Certificate of Origin" },
  { value: "delivery_challan", label: "Delivery Challan" },
  { value: "contract", label: "Contract" },
  { value: "receipt", label: "Receipt" },
  { value: "customs_document", label: "Customs Document" },
  { value: "shipping_document", label: "Shipping Document" },
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
}: DocumentFiltersProps) {
  const hasActiveFilters = search || documentType || status;

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-sm">
      <div className="flex flex-1 items-center gap-2 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by filename or ID..."
            className="pl-9 text-xs h-9 bg-slate-50/50 dark:bg-slate-800/50"
          />
          {search && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* Document Type Filter */}
        <select
          value={documentType}
          onChange={(e) => onDocumentTypeChange(e.target.value as DocumentType | "")}
          className="h-9 px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
        >
          <option value="">All Document Types</option>
          {DOCUMENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>

        {/* Status Filter */}
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value as DocumentStatus | "")}
          className="h-9 px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-9 px-2.5 text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
          >
            <X className="w-3.5 h-3.5 mr-1" />
            Reset
          </Button>
        )}
      </div>
    </div>
  );
}
