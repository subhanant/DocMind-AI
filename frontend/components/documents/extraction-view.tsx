/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState } from "react";
import { ExtractionResult } from "@/types";
import {
  Calendar,
  CheckCircle2,
  Copy,
  DollarSign,
  Download,
  Edit3,
  FileJson,
  FileText,
  Flame,
  Info,
  Package,
  RefreshCw,
  Save,
  Search,
  Ship,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import {
  confidenceLevel,
  ConfidenceBadge,
  ConfidenceRing,
} from "@/components/ui/confidence";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert } from "@/components/ui/alert";
import { Table, TableWrapper, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { cn, formatConfidence, formatDocType } from "@/lib/utils";

interface ExtractionViewProps {
  extraction: ExtractionResult | null;
  documentId: string;
  documentType: string;
  onExtractionUpdated?: (newExtraction: ExtractionResult) => void;
}

interface FieldValue {
  value: string | null;
  confidence: number;
  source_text?: string;
  page?: number;
}

type FieldDef = {
  label: string;
  paths: string[];
  evidenceKeys: string[];
  editKey?: string;
};

type SectionDef = {
  key: string;
  title: string;
  icon: React.ElementType;
  iconClass: string;
  fields: FieldDef[];
};

const SECTIONS: SectionDef[] = [
  {
    key: "document",
    title: "Document information",
    icon: FileText,
    iconClass: "text-brand-600 dark:text-brand-300",
    fields: [
      {
        label: "B/L Number",
        paths: ["document_metadata.bl_number", "bl_number"],
        evidenceKeys: ["bl_number"],
        editKey: "bl_number",
      },
      {
        label: "B/L Date",
        paths: ["document_metadata.bl_date", "bl_date", "issue_date", "dates.bl_date", "dates.issue_date"],
        evidenceKeys: ["bl_date", "issue_date"],
        editKey: "bl_date",
      },
      {
        label: "B/L Type",
        paths: ["document_metadata.bl_type", "bl_type"],
        evidenceKeys: ["bl_type"],
        editKey: "bl_type",
      },
      {
        label: "B/L Status",
        paths: ["document_metadata.bl_status", "bl_status"],
        evidenceKeys: ["bl_status"],
        editKey: "bl_status",
      },
      {
        label: "Place of Issue",
        paths: ["document_metadata.place_of_issue", "place_of_issue"],
        evidenceKeys: ["place_of_issue"],
        editKey: "place_of_issue",
      },
      {
        label: "Original Copies",
        paths: ["document_metadata.original_copies", "original_copies"],
        evidenceKeys: ["original_copies"],
        editKey: "original_copies",
      },
    ],
  },
  {
    key: "parties",
    title: "Parties",
    icon: UserCheck,
    iconClass: "text-indigo-500",
    fields: [
      {
        label: "Shipper Name",
        paths: ["parties.shipper.name", "shipper.name", "shipper"],
        evidenceKeys: ["shipper_name", "shipper.name"],
        editKey: "shipper_name",
      },
      {
        label: "Shipper Address",
        paths: ["parties.shipper.address", "shipper.address"],
        evidenceKeys: ["shipper_address", "shipper.address"],
        editKey: "shipper_address",
      },
      {
        label: "Consignee Name",
        paths: ["parties.consignee.name", "consignee.name", "consignee"],
        evidenceKeys: ["consignee_name", "consignee.name"],
        editKey: "consignee_name",
      },
      {
        label: "Consignee Address",
        paths: ["parties.consignee.address", "consignee.address"],
        evidenceKeys: ["consignee_address", "consignee.address"],
        editKey: "consignee_address",
      },
      {
        label: "Notify Party Name",
        paths: ["parties.notify_party.name", "notify_party.name", "notify_party"],
        evidenceKeys: ["notify_party_name", "notify_party.name"],
        editKey: "notify_party_name",
      },
      {
        label: "Notify Party Address",
        paths: ["parties.notify_party.address", "notify_party.address"],
        evidenceKeys: ["notify_party_address", "notify_party.address"],
        editKey: "notify_party_address",
      },
    ],
  },
  {
    key: "shipment",
    title: "Shipment",
    icon: Ship,
    iconClass: "text-cyan-500",
    fields: [
      {
        label: "Carrier",
        paths: ["shipment.carrier", "carrier", "shipment.shipping_line", "shipping_line"],
        evidenceKeys: ["carrier", "shipping_line"],
        editKey: "carrier",
      },
      {
        label: "Vessel Name",
        paths: ["shipment.vessel_name", "vessel_name"],
        evidenceKeys: ["vessel_name"],
        editKey: "vessel_name",
      },
      {
        label: "Voyage Number",
        paths: ["shipment.voyage_number", "voyage_number"],
        evidenceKeys: ["voyage_number"],
        editKey: "voyage_number",
      },
      {
        label: "Place of Receipt",
        paths: ["shipment.place_of_receipt", "place_of_receipt"],
        evidenceKeys: ["place_of_receipt"],
        editKey: "place_of_receipt",
      },
      {
        label: "Port of Loading (POL)",
        paths: ["shipment.port_of_loading", "port_of_loading"],
        evidenceKeys: ["port_of_loading"],
        editKey: "port_of_loading",
      },
      {
        label: "Port of Discharge (POD)",
        paths: ["shipment.port_of_discharge", "port_of_discharge"],
        evidenceKeys: ["port_of_discharge"],
        editKey: "port_of_discharge",
      },
      {
        label: "Place of Delivery",
        paths: ["shipment.place_of_delivery", "place_of_delivery", "final_destination"],
        evidenceKeys: ["place_of_delivery", "final_destination"],
        editKey: "place_of_delivery",
      },
    ],
  },
  {
    key: "dates",
    title: "Dates",
    icon: Calendar,
    iconClass: "text-rose-500",
    fields: [
      {
        label: "On Board Date",
        paths: ["dates.on_board_date", "on_board_date"],
        evidenceKeys: ["on_board_date"],
        editKey: "on_board_date",
      },
      {
        label: "Issue Date",
        paths: ["document_metadata.bl_date", "bl_date", "dates.issue_date", "dates.bl_date"],
        evidenceKeys: ["bl_date", "issue_date"],
        editKey: "bl_date",
      },
    ],
  },
  {
    key: "cargo",
    title: "Cargo",
    icon: Package,
    iconClass: "text-amber-500",
    fields: [
      {
        label: "Cargo Description",
        paths: ["cargo.description", "description", "cargo.commodity", "commodity"],
        evidenceKeys: ["cargo_description", "description"],
        editKey: "description",
      },
      {
        label: "HS Code",
        paths: ["cargo.hs_code", "hs_code"],
        evidenceKeys: ["hs_code"],
        editKey: "hs_code",
      },
      {
        label: "Marks & Numbers",
        paths: ["cargo.marks_and_numbers", "marks_and_numbers"],
        evidenceKeys: ["marks_and_numbers"],
        editKey: "marks_and_numbers",
      },
      {
        label: "Number of Packages",
        paths: ["cargo.number_of_packages", "number_of_packages", "cargo.package_type"],
        evidenceKeys: ["number_of_packages"],
        editKey: "number_of_packages",
      },
      {
        label: "Gross Weight",
        paths: ["cargo.gross_weight", "gross_weight"],
        evidenceKeys: ["gross_weight"],
        editKey: "gross_weight",
      },
      {
        label: "Net Weight",
        paths: ["cargo.net_weight", "net_weight"],
        evidenceKeys: ["net_weight"],
        editKey: "net_weight",
      },
      {
        label: "CBM / Volume",
        paths: ["cargo.cbm", "cbm", "cargo.volume", "volume"],
        evidenceKeys: ["cbm", "volume"],
        editKey: "cbm",
      },
    ],
  },
  {
    key: "freight",
    title: "Freight",
    icon: DollarSign,
    iconClass: "text-emerald-500",
    fields: [
      {
        label: "Freight Terms",
        paths: ["freight.terms", "freight_terms"],
        evidenceKeys: ["freight_terms"],
        editKey: "freight_terms",
      },
      {
        label: "Freight Amount",
        paths: ["freight.amount", "freight_amount", "prepaid_amount", "collect_amount"],
        evidenceKeys: ["freight_amount"],
        editKey: "freight_amount",
      },
      {
        label: "Currency",
        paths: ["freight.currency", "freight_currency", "currency"],
        evidenceKeys: ["currency", "freight_currency"],
        editKey: "currency",
      },
    ],
  },
  {
    key: "references",
    title: "References",
    icon: Info,
    iconClass: "text-violet-500",
    fields: [
      {
        label: "Booking Number",
        paths: ["shipment.booking_number", "booking_number"],
        evidenceKeys: ["booking_number"],
        editKey: "booking_number",
      },
      {
        label: "Invoice Number",
        paths: ["references.invoice_number", "invoice_number"],
        evidenceKeys: ["invoice_number"],
        editKey: "invoice_number",
      },
      {
        label: "Purchase Order No.",
        paths: ["references.purchase_order_number", "purchase_order_number"],
        evidenceKeys: ["purchase_order_number"],
        editKey: "purchase_order_number",
      },
    ],
  },
];

const VALIDATION_BADGES: Record<
  ExtractionResult["validation_status"],
  { variant: "success" | "warning" | "destructive" | "neutral"; label: string }
> = {
  valid: { variant: "success", label: "Validated" },
  partial: { variant: "warning", label: "Partially validated" },
  invalid: { variant: "destructive", label: "Validation failed" },
  pending: { variant: "neutral", label: "Awaiting validation" },
};

function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/** Shown when a document is stored but has not been through the AI pipeline. */
function NotProcessedCard({
  documentId,
  onExtractionUpdated,
}: {
  documentId: string;
  onExtractionUpdated?: (extraction: ExtractionResult) => void;
}) {
  const toast = useToast();
  const [isReprocessing, setIsReprocessing] = useState(false);

  const handleReprocess = async () => {
    try {
      setIsReprocessing(true);
      const res = await api.documents.reprocess(documentId);
      onExtractionUpdated?.(res);
      toast.success(
        "Extraction complete",
        "The document was processed by the AI pipeline."
      );
    } catch {
      toast.error(
        "Extraction failed",
        "The document could not be processed. Please try again."
      );
    } finally {
      setIsReprocessing(false);
    }
  };

  return (
    <Card className="overflow-hidden">
      <EmptyState
        icon={Sparkles}
        title="AI extraction has not run yet"
        description="This document is stored but no structured fields have been extracted. Run the pipeline to classify it and extract every field with confidence scores."
        action={
          <Button onClick={handleReprocess} disabled={isReprocessing} className="gap-2">
            <RefreshCw className={cn("h-4 w-4", isReprocessing && "animate-spin")} />
            {isReprocessing ? "Extracting…" : "Run AI extraction now"}
          </Button>
        }
      />
      <div className="border-t border-line bg-surface-muted/50 px-6 py-4">
        <ol className="mx-auto flex max-w-md flex-wrap items-center justify-center gap-x-2 gap-y-1 text-[11px] font-medium text-ink-subtle">
          {["Upload", "OCR", "Classify", "Extract", "Validate"].map((stage, index, all) => (
            <li key={stage} className="flex items-center gap-2">
              <span className="rounded-md border border-line bg-surface px-1.5 py-0.5">
                {stage}
              </span>
              {index < all.length - 1 && (
                <span aria-hidden>→</span>
              )}
            </li>
          ))}
        </ol>
      </div>
    </Card>
  );
}

export function ExtractionView({
  extraction,
  documentId,
  documentType,
  onExtractionUpdated,
}: ExtractionViewProps) {
  const hasExtractedData = Boolean(
    extraction &&
      extraction.extracted_json &&
      Object.keys(extraction.extracted_json).length > 0 &&
      extraction.extracted_json.status !== "unimplemented"
  );

  if (!hasExtractedData || !extraction) {
    return (
      <NotProcessedCard
        documentId={documentId}
        onExtractionUpdated={onExtractionUpdated}
      />
    );
  }

  return (
    <ExtractionResults
      // Remount when the backend returns a new extraction so edit state resets.
      key={`${extraction.id}-${extraction.updated_at}`}
      extraction={extraction}
      documentId={documentId}
      documentType={documentType}
      onExtractionUpdated={onExtractionUpdated}
    />
  );
}

function ExtractionResults({
  extraction,
  documentId,
  documentType,
  onExtractionUpdated,
}: ExtractionViewProps & { extraction: ExtractionResult }) {
  const toast = useToast();

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editFormData, setEditFormData] = useState<Record<string, string>>({});
  const [fieldQuery, setFieldQuery] = useState("");
  const [showEmptyFields, setShowEmptyFields] = useState(true);
  const [showRawJson, setShowRawJson] = useState(false);

  const rawData = (extraction.extracted_json || {}) as Record<string, any>;
  const fieldEvidence = (extraction.field_evidence ||
    rawData.field_evidence ||
    {}) as Record<string, any>;

  /** Resolves a field from `field_evidence` first, then nested `extracted_json` paths. */
  const getField = (
    paths: string[],
    evidenceKeys: string[] = []
  ): FieldValue | undefined => {
    let evMatch: any = undefined;
    for (const key of evidenceKeys) {
      if (fieldEvidence && fieldEvidence[key]) {
        evMatch = fieldEvidence[key];
        break;
      }
    }

    let rawVal: any = undefined;
    for (const path of paths) {
      const parts = path.split(".");
      let current: any = rawData;
      for (const part of parts) {
        if (current && typeof current === "object" && part in current) {
          current = current[part];
        } else {
          current = undefined;
          break;
        }
      }
      if (current !== undefined && current !== null) {
        rawVal = current;
        break;
      }
    }

    if (
      rawVal === undefined &&
      (!evMatch || evMatch.value === undefined || evMatch.value === null)
    ) {
      return undefined;
    }

    let finalVal: any = null;
    if (evMatch && evMatch.value !== undefined && evMatch.value !== null) {
      finalVal = evMatch.value;
    } else if (rawVal !== undefined && rawVal !== null) {
      finalVal = rawVal;
    }

    // Extracted-field wrapper: { value, confidence, source_text }
    if (
      finalVal &&
      typeof finalVal === "object" &&
      "value" in finalVal &&
      !("unit" in finalVal)
    ) {
      if (finalVal.confidence !== undefined && (!evMatch || !evMatch.confidence)) {
        evMatch = { ...evMatch, confidence: finalVal.confidence };
      }
      if (finalVal.source_text && (!evMatch || !evMatch.source_text)) {
        evMatch = { ...evMatch, source_text: finalVal.source_text };
      }
      finalVal = finalVal.value;
    }

    // Measurement wrapper: { value, unit }
    if (finalVal && typeof finalVal === "object" && "value" in finalVal) {
      const value = finalVal.value;
      const unit = finalVal.unit ? ` ${finalVal.unit}` : "";
      if (value === null || value === undefined) return undefined;
      finalVal =
        typeof value === "number"
          ? `${value.toLocaleString()}${unit}`
          : `${value}${unit}`;
    }

    if (finalVal === null || finalVal === undefined || finalVal === "") {
      return undefined;
    }

    return {
      value: String(finalVal),
      confidence: evMatch?.confidence ?? extraction.confidence_score ?? 0.9,
      source_text: evMatch?.source_text ?? undefined,
      page: evMatch?.page ?? undefined,
    };
  };

  const handleStartEdit = () => {
    const initialData: Record<string, string> = {};
    for (const section of SECTIONS) {
      for (const field of section.fields) {
        if (!field.editKey) continue;
        const value = getField(field.paths, field.evidenceKeys);
        initialData[field.editKey] = value?.value ? String(value.value) : "";
      }
    }
    setEditFormData(initialData);
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    setIsSaving(true);
    try {
      const updatedJson = JSON.parse(JSON.stringify(rawData)) as Record<string, any>;

      const setNested = (obj: Record<string, any>, path: string, value: unknown) => {
        const parts = path.split(".");
        let current = obj;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!current[parts[i]]) current[parts[i]] = {};
          current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
      };

      const write = (editKey: string, path: string) => {
        if (editFormData[editKey] === undefined) return;
        setNested(updatedJson, path, editFormData[editKey] || null);
      };

      write("bl_number", "document_metadata.bl_number");
      write("bl_date", "document_metadata.bl_date");
      write("bl_type", "document_metadata.bl_type");
      write("bl_status", "document_metadata.bl_status");
      write("place_of_issue", "document_metadata.place_of_issue");
      write("original_copies", "document_metadata.original_copies");
      write("shipper_name", "parties.shipper.name");
      write("shipper_address", "parties.shipper.address");
      write("consignee_name", "parties.consignee.name");
      write("consignee_address", "parties.consignee.address");
      write("notify_party_name", "parties.notify_party.name");
      write("notify_party_address", "parties.notify_party.address");
      write("carrier", "shipment.carrier");
      write("vessel_name", "shipment.vessel_name");
      write("voyage_number", "shipment.voyage_number");
      write("place_of_receipt", "shipment.place_of_receipt");
      write("port_of_loading", "shipment.port_of_loading");
      write("port_of_discharge", "shipment.port_of_discharge");
      write("place_of_delivery", "shipment.place_of_delivery");
      write("on_board_date", "dates.on_board_date");
      write("description", "cargo.description");
      write("hs_code", "cargo.hs_code");
      write("marks_and_numbers", "cargo.marks_and_numbers");
      write("number_of_packages", "cargo.number_of_packages");
      write("gross_weight", "cargo.gross_weight");
      write("net_weight", "cargo.net_weight");
      write("cbm", "cargo.cbm");
      write("freight_terms", "freight.terms");
      write("freight_amount", "freight.amount");
      write("currency", "freight.currency");
      write("booking_number", "shipment.booking_number");
      write("invoice_number", "references.invoice_number");
      write("purchase_order_number", "references.purchase_order_number");

      const res = await api.documents.updateExtraction(documentId, updatedJson);
      setIsEditing(false);
      onExtractionUpdated?.(res);
      toast.success("Changes saved", "The extracted fields were updated.");
    } catch {
      toast.error("Save failed", "The updated extraction could not be saved.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleReprocess = async () => {
    try {
      setIsReprocessing(true);
      const res = await api.documents.reprocess(documentId);
      onExtractionUpdated?.(res);
      toast.success(
        "Re-extraction complete",
        "The document was processed by the AI pipeline again."
      );
    } catch {
      toast.error(
        "Re-extraction failed",
        "The document could not be processed. Please try again."
      );
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(rawData, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Copy failed", "Clipboard access was denied by the browser.");
    }
  };

  const handleDownloadJson = () => {
    downloadFile(
      JSON.stringify(rawData, null, 2),
      `extraction_${documentId.slice(0, 8)}.json`,
      "application/json"
    );
  };

  const handleDownloadCsv = () => {
    const rows: (string | number)[][] = [
      ["Section", "Field", "Value", "Confidence %", "Source snippet"],
    ];
    const escape = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;

    for (const section of SECTIONS) {
      for (const field of section.fields) {
        const resolved = getField(field.paths, field.evidenceKeys);
        rows.push([
          section.title,
          field.label,
          resolved?.value ?? "",
          resolved ? Math.round(resolved.confidence * 100) : "",
          resolved?.source_text ?? "",
        ]);
      }
    }

    const csv = rows.map((row) => row.map(escape).join(",")).join("\n");
    downloadFile(csv, `extraction_${documentId.slice(0, 8)}.csv`, "text/csv;charset=utf-8;");
  };

  // Resolve every field once per render so counters, filters and rows agree.
  const resolvedSections = SECTIONS.map((section) => {
    const entries = section.fields.map((field) => ({
      field,
      value: getField(field.paths, field.evidenceKeys),
    }));

    const query = fieldQuery.trim().toLowerCase();
    const visible = entries.filter(({ field, value }) => {
      if (!showEmptyFields && !value) return false;
      if (!query) return true;
      return (
        field.label.toLowerCase().includes(query) ||
        (value?.value ?? "").toLowerCase().includes(query)
      );
    });

    return { ...section, entries, visible };
  });

  const allFields = resolvedSections.flatMap((section) =>
    section.entries.map((entry) => entry.value)
  );
  const extractedCount = allFields.filter(Boolean).length;
  const totalCount = allFields.length;
  const averageConfidence =
    extractedCount > 0
      ? allFields.reduce((sum, field) => sum + (field?.confidence ?? 0), 0) / extractedCount
      : null;

  const containersList = Array.isArray(rawData.containers) ? rawData.containers : [];
  const dangerousGoods = rawData.dangerous_goods;
  const validation =
    VALIDATION_BADGES[extraction.validation_status] ?? VALIDATION_BADGES.pending;
  const hasDangerousGoods = Boolean(
    dangerousGoods &&
      (dangerousGoods.un_number?.value ||
        dangerousGoods.imo_class?.value ||
        dangerousGoods.un_number ||
        dangerousGoods.imo_class)
  );

  const visibleSections = resolvedSections.filter((section) => section.visible.length > 0);

  const renderField = (field: FieldDef) => {
    const resolved = getField(field.paths, field.evidenceKeys);
    const formKey = field.editKey ?? field.paths[0].replace(/\./g, "_");

    if (isEditing) {
      return (
        <div key={field.label} className="space-y-1.5 rounded-xl bg-surface-muted/60 p-3">
          <label
            htmlFor={`edit-${formKey}`}
            className="block text-[11px] font-semibold uppercase tracking-wide text-ink-subtle"
          >
            {field.label}
          </label>
          <Input
            id={`edit-${formKey}`}
            value={editFormData[formKey] ?? (resolved?.value ? String(resolved.value) : "")}
            onChange={(event) =>
              setEditFormData((prev) => ({ ...prev, [formKey]: event.target.value }))
            }
            className="h-9 text-sm"
          />
        </div>
      );
    }

    if (!resolved) {
      return (
        <div
          key={field.label}
          className="flex items-baseline justify-between gap-3 border-b border-line/60 py-2.5 last:border-0"
        >
          <span className="text-xs font-medium text-ink-muted">{field.label}</span>
          <span className="text-xs italic text-ink-subtle">Not extracted</span>
        </div>
      );
    }

    const level = confidenceLevel(resolved.confidence);

    return (
      <div
        key={field.label}
        className="border-b border-line/60 py-2.5 transition-colors last:border-0 hover:bg-surface-hover/50"
      >
        <div className="flex items-start justify-between gap-3">
          <span className="text-xs font-medium text-ink-muted">{field.label}</span>
          <div className="flex shrink-0 items-center gap-1.5">
            {resolved.page !== undefined && resolved.page !== null && (
              <span className="rounded border border-line bg-surface-muted px-1 py-px text-[10px] text-ink-subtle">
                p.{resolved.page}
              </span>
            )}
            <ConfidenceBadge score={resolved.confidence} showIcon />
          </div>
        </div>

        <p
          className={cn(
            "mt-1 break-words text-sm font-semibold leading-snug text-ink",
            level === "low" && "text-rose-700 dark:text-rose-300"
          )}
        >
          {resolved.value}
        </p>

        {resolved.source_text && (
          <p className="mt-1.5 border-l-2 border-line bg-surface-muted/70 px-2 py-1 font-mono text-[10px] leading-relaxed text-ink-muted">
            &ldquo;{resolved.source_text}&rdquo;
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-5">
      {/* Overview + toolbar */}
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-5 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <ConfidenceRing score={extraction.confidence_score} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-semibold text-ink">
                  {formatDocType(documentType || "bill_of_lading")} extraction
                </h2>
                <Badge variant="neutral" size="sm">
                  v{extraction.schema_version || "2.0"}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge variant={validation.variant} size="sm">
                  <CheckCircle2 className="h-3 w-3" />
                  {validation.label}
                </Badge>
                <span className="text-xs text-ink-muted tabular">
                  {extractedCount} of {totalCount} fields extracted
                  {averageConfidence !== null && (
                    <>
                      {" · avg "}
                      <span className="font-semibold text-ink">
                        {formatConfidence(averageConfidence)}
                      </span>
                    </>
                  )}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {isEditing ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditing(false)}
                  disabled={isSaving}
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveEdit} disabled={isSaving}>
                  {isSaving ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="h-3.5 w-3.5" />
                  )}
                  {isSaving ? "Saving…" : "Save changes"}
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={handleStartEdit}>
                  <Edit3 className="h-3.5 w-3.5" />
                  Edit fields
                </Button>
                <Button variant="outline" size="sm" onClick={handleCopyJson}>
                  {copied ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  {copied ? "Copied" : "Copy JSON"}
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadJson}>
                  <FileJson className="h-3.5 w-3.5" />
                  JSON
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadCsv}>
                  <Download className="h-3.5 w-3.5" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReprocess}
                  disabled={isReprocessing}
                >
                  <RefreshCw className={cn("h-3.5 w-3.5", isReprocessing && "animate-spin")} />
                  {isReprocessing ? "Processing…" : "Re-extract"}
                </Button>
              </>
            )}
          </div>
        </div>

        {!isEditing && (
          <div className="flex flex-col gap-3 border-t border-line bg-surface-muted/50 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="w-full sm:max-w-xs">
              <Input
                type="search"
                value={fieldQuery}
                onChange={(event) => setFieldQuery(event.target.value)}
                placeholder="Filter extracted fields…"
                aria-label="Filter extracted fields"
                leadingIcon={<Search />}
                className="h-9 bg-surface [&::-webkit-search-cancel-button]:hidden"
              />
            </div>

            <div className="flex items-center gap-4">
              <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-muted">
                <input
                  type="checkbox"
                  checked={showEmptyFields}
                  onChange={(event) => setShowEmptyFields(event.target.checked)}
                  className="focus-ring h-3.5 w-3.5 cursor-pointer rounded border-line-strong accent-brand-600"
                />
                Show empty fields
              </label>
              <button
                type="button"
                onClick={() => setShowRawJson((open) => !open)}
                className="focus-ring rounded text-xs font-semibold text-brand-600 transition-colors hover:text-brand-700 dark:text-brand-300"
                aria-expanded={showRawJson}
              >
                {showRawJson ? "Hide raw JSON" : "View raw JSON"}
              </button>
            </div>
          </div>
        )}

        {showRawJson && !isEditing && (
          <div className="border-t border-line bg-surface-muted/40 p-5">
            <pre className="max-h-80 overflow-auto rounded-xl border border-line bg-surface p-4 font-mono text-[11px] leading-relaxed text-ink-muted">
              {JSON.stringify(rawData, null, 2)}
            </pre>
          </div>
        )}
      </Card>

      {isEditing && (
        <Alert variant="info" title="Editing extracted fields" role="status">
          Corrections are written back to the extraction record and tracked in the audit history.
        </Alert>
      )}

      {/* Dangerous goods */}
      {hasDangerousGoods && (
        <div className="flex items-start gap-4 rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 p-5 dark:border-amber-900/60 dark:from-amber-950/30 dark:to-orange-950/20">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-soft [&_svg]:size-5">
            <Flame />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">
              IMDG dangerous goods detected
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-amber-800/90 dark:text-amber-300/90">
              This shipment contains hazardous cargo regulated under the International Maritime
              Dangerous Goods Code.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(dangerousGoods.un_number?.value || dangerousGoods.un_number) && (
                <span className="rounded-lg border border-amber-300 bg-amber-100/80 px-3 py-1.5 font-mono text-xs font-bold text-amber-900 dark:border-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
                  UN {dangerousGoods.un_number?.value || dangerousGoods.un_number}
                </span>
              )}
              {(dangerousGoods.imo_class?.value || dangerousGoods.imo_class) && (
                <span className="rounded-lg border border-amber-300 bg-amber-100/80 px-3 py-1.5 font-mono text-xs font-bold text-amber-900 dark:border-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
                  IMO class {dangerousGoods.imo_class?.value || dangerousGoods.imo_class}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Field sections */}
      {visibleSections.length === 0 ? (
        <Card>
          <EmptyState
            compact
            icon={Search}
            title="No fields match your filter"
            description="Try a different search term or re-enable empty fields."
            action={
              <Button variant="outline" size="sm" onClick={() => setFieldQuery("")}>
                Clear filter
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          {visibleSections.map((section) => (
            <Card key={section.key} className="overflow-hidden">
              <div className="flex items-center gap-2.5 border-b border-line px-5 py-3.5">
                <section.icon className={cn("h-4 w-4", section.iconClass)} aria-hidden />
                <h3 className="text-sm font-semibold text-ink">{section.title}</h3>
                <span className="ml-auto rounded-md bg-surface-muted px-1.5 py-0.5 text-[10px] font-semibold tabular text-ink-subtle">
                  {section.visible.filter((entry) => entry.value).length}/
                  {section.entries.length}
                </span>
              </div>
              <div
                className={cn(
                  "px-5 py-2",
                  isEditing && "grid grid-cols-1 gap-3 py-4 sm:grid-cols-2"
                )}
              >
                {section.visible.map(({ field }) => renderField(field))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Containers */}
      {containersList.length > 0 && (
        <Card className="overflow-hidden">
          <div className="flex items-center gap-2.5 border-b border-line px-5 py-3.5">
            <Package className="h-4 w-4 text-brand-500" aria-hidden />
            <h3 className="text-sm font-semibold text-ink">Containers</h3>
            <Badge variant="neutral" size="sm" className="ml-auto">
              {containersList.length}
            </Badge>
          </div>
          <TableWrapper>
            <Table>
              <thead>
                <tr>
                  <Th>Container number</Th>
                  <Th>Seal number</Th>
                  <Th>Type</Th>
                  <Th className="text-right">Confidence</Th>
                </tr>
              </thead>
              <tbody>
                {containersList.map((container: any, index: number) => {
                  const number =
                    container.container_number?.value || container.container_number || "—";
                  const seal =
                    container.seal_number?.value || container.seal_number || "—";
                  const type =
                    container.container_type?.value ||
                    container.container_size?.value ||
                    container.container_type ||
                    "—";
                  const confidence =
                    container.container_number?.confidence ??
                    extraction.confidence_score ??
                    0.95;

                  return (
                    <Tr key={index}>
                      <Td className="font-mono text-xs font-semibold text-brand-700 dark:text-brand-300">
                        {number}
                      </Td>
                      <Td className="font-mono text-xs text-ink-muted">{seal}</Td>
                      <Td>
                        <span className="rounded-md border border-line bg-surface-muted px-2 py-0.5 text-[11px] font-medium text-ink-muted">
                          {type}
                        </span>
                      </Td>
                      <Td className="text-right">
                        <ConfidenceBadge score={confidence} />
                      </Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          </TableWrapper>
        </Card>
      )}
    </div>
  );
}
