"use client";

import React, { useState } from "react";
import { ExtractionResult } from "@/types";
import {
  FileText,
  Ship,
  Calendar,
  Package,
  DollarSign,
  Info,
  CheckCircle2,
  Clock,
  Edit3,
  Save,
  X,
  Download,
  Copy,
  Check,
  RefreshCw,
  Container,
  UserCheck,
  Flame,
} from "lucide-react";
import { formatConfidence, formatDocType } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface ExtractionViewProps {
  extraction: ExtractionResult | null;
  documentId: string;
  documentType: string;
  onExtractionUpdated?: (newExtraction: ExtractionResult) => void;
}

interface FieldValue {
  value: string | number | null;
  confidence: number;
  source_text?: string;
  page?: number;
}

export function ExtractionView({
  extraction,
  documentId,
  documentType,
  onExtractionUpdated,
}: ExtractionViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editFormData, setEditFormData] = useState<Record<string, string>>({});

  const hasExtractedData =
    extraction &&
    extraction.extracted_json &&
    Object.keys(extraction.extracted_json).length > 0 &&
    extraction.extracted_json.status !== "unimplemented";

  if (!hasExtractedData) {
    return (
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 backdrop-blur-sm p-10 text-center shadow-sm">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 dark:bg-blue-950/50 mx-auto text-blue-600 dark:text-blue-400 mb-4 ring-8 ring-blue-50/50 dark:ring-blue-950/20">
          <Clock className="w-7 h-7 animate-pulse" />
        </div>
        <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          Extraction In Progress or Queued
        </h4>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-2 leading-relaxed">
          The document text and layout are being processed. Click below to trigger or re-run the AI extraction pipeline.
        </p>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button
            onClick={async () => {
              try {
                setIsReprocessing(true);
                const res = await api.documents.reprocess(documentId);
                if (onExtractionUpdated) onExtractionUpdated(res);
              } catch {
                alert("Failed to process document.");
              } finally {
                setIsReprocessing(false);
              }
            }}
            disabled={isReprocessing}
            className="bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isReprocessing ? "animate-spin" : ""}`} />
            {isReprocessing ? "Extracting..." : "Run AI Extraction Now"}
          </Button>
        </div>
      </div>
    );
  }

  const rawData = (extraction.extracted_json || {}) as Record<string, any>;
  const fieldEvidence = (extraction.field_evidence || rawData.field_evidence || {}) as Record<string, any>;

  // Flexible field resolver supporting nested Phase 2 schema & field evidence
  const getField = (
    paths: string[],
    evidenceKeys: string[] = []
  ): FieldValue | undefined => {
    // 1. Check field_evidence for matching key
    let evMatch: any = undefined;
    for (const k of evidenceKeys) {
      if (fieldEvidence && fieldEvidence[k]) {
        evMatch = fieldEvidence[k];
        break;
      }
    }

    // 2. Check extracted_json at each path
    let rawVal: any = undefined;
    for (const p of paths) {
      const parts = p.split(".");
      let curr: any = rawData;
      for (const part of parts) {
        if (curr && typeof curr === "object" && part in curr) {
          curr = curr[part];
        } else {
          curr = undefined;
          break;
        }
      }
      if (curr !== undefined && curr !== null) {
        rawVal = curr;
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

    // If finalVal is an extracted field wrapper { value, confidence }
    if (finalVal && typeof finalVal === "object" && "value" in finalVal && !("unit" in finalVal)) {
      if (finalVal.confidence !== undefined && (!evMatch || !evMatch.confidence)) {
        evMatch = { ...evMatch, confidence: finalVal.confidence };
      }
      if (finalVal.source_text && (!evMatch || !evMatch.source_text)) {
        evMatch = { ...evMatch, source_text: finalVal.source_text };
      }
      finalVal = finalVal.value;
    }

    // If finalVal is a Measurement { value, unit }
    if (finalVal && typeof finalVal === "object" && "value" in finalVal) {
      const v = finalVal.value;
      const u = finalVal.unit ? ` ${finalVal.unit}` : "";
      if (v === null || v === undefined) {
        return undefined;
      }
      finalVal = typeof v === "number" ? `${v.toLocaleString()}${u}` : `${v}${u}`;
    }

    if (finalVal === null || finalVal === undefined || finalVal === "") {
      return undefined;
    }

    const conf = evMatch?.confidence ?? extraction.confidence_score ?? 0.90;
    const source_text = evMatch?.source_text ?? undefined;
    const page = evMatch?.page ?? undefined;

    return {
      value: String(finalVal),
      confidence: conf,
      source_text,
      page,
    };
  };

  const fieldsToEditMap: Array<{ key: string; paths: string[]; evKeys: string[] }> = [
    { key: "bl_number", paths: ["document_metadata.bl_number", "bl_number"], evKeys: ["bl_number"] },
    { key: "bl_date", paths: ["document_metadata.bl_date", "bl_date", "dates.issue_date"], evKeys: ["bl_date", "issue_date"] },
    { key: "bl_type", paths: ["document_metadata.bl_type", "bl_type"], evKeys: ["bl_type"] },
    { key: "shipper_name", paths: ["parties.shipper.name", "shipper.name"], evKeys: ["shipper_name", "shipper.name"] },
    { key: "shipper_address", paths: ["parties.shipper.address", "shipper.address"], evKeys: ["shipper_address", "shipper.address"] },
    { key: "consignee_name", paths: ["parties.consignee.name", "consignee.name"], evKeys: ["consignee_name", "consignee.name"] },
    { key: "consignee_address", paths: ["parties.consignee.address", "consignee.address"], evKeys: ["consignee_address", "consignee.address"] },
    { key: "notify_party_name", paths: ["parties.notify_party.name", "notify_party.name"], evKeys: ["notify_party_name", "notify_party.name"] },
    { key: "carrier", paths: ["shipment.carrier", "carrier", "shipment.shipping_line", "shipping_line"], evKeys: ["carrier", "shipping_line"] },
    { key: "vessel_name", paths: ["shipment.vessel_name", "vessel_name"], evKeys: ["vessel_name"] },
    { key: "voyage_number", paths: ["shipment.voyage_number", "voyage_number"], evKeys: ["voyage_number"] },
    { key: "port_of_loading", paths: ["shipment.port_of_loading", "port_of_loading"], evKeys: ["port_of_loading"] },
    { key: "port_of_discharge", paths: ["shipment.port_of_discharge", "port_of_discharge"], evKeys: ["port_of_discharge"] },
    { key: "place_of_delivery", paths: ["shipment.place_of_delivery", "place_of_delivery"], evKeys: ["place_of_delivery"] },
    { key: "on_board_date", paths: ["dates.on_board_date", "on_board_date"], evKeys: ["on_board_date"] },
    { key: "description", paths: ["cargo.description", "description", "cargo.commodity"], evKeys: ["cargo_description", "description"] },
    { key: "hs_code", paths: ["cargo.hs_code", "hs_code"], evKeys: ["hs_code"] },
    { key: "number_of_packages", paths: ["cargo.number_of_packages", "number_of_packages"], evKeys: ["number_of_packages"] },
    { key: "gross_weight", paths: ["cargo.gross_weight", "gross_weight"], evKeys: ["gross_weight"] },
    { key: "net_weight", paths: ["cargo.net_weight", "net_weight"], evKeys: ["net_weight"] },
    { key: "cbm", paths: ["cargo.cbm", "cbm", "cargo.volume", "volume"], evKeys: ["cbm", "volume"] },
    { key: "freight_terms", paths: ["freight.terms", "freight_terms"], evKeys: ["freight_terms"] },
    { key: "freight_amount", paths: ["freight.amount", "freight_amount"], evKeys: ["freight_amount"] },
    { key: "currency", paths: ["freight.currency", "freight_currency", "currency"], evKeys: ["currency", "freight_currency"] },
    { key: "booking_number", paths: ["shipment.booking_number", "booking_number"], evKeys: ["booking_number"] },
    { key: "invoice_number", paths: ["references.invoice_number", "invoice_number"], evKeys: ["invoice_number"] },
  ];

  const handleStartEdit = () => {
    const initialData: Record<string, string> = {};
    for (const f of fieldsToEditMap) {
      const val = getField(f.paths, f.evKeys);
      initialData[f.key] = val?.value ? String(val.value) : "";
    }
    setEditFormData(initialData);
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    setIsSaving(true);
    try {
      const updatedJson = JSON.parse(JSON.stringify(rawData));

      // Helper to set nested property
      const setNested = (obj: any, path: string, val: any) => {
        const parts = path.split(".");
        let curr = obj;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!curr[parts[i]]) curr[parts[i]] = {};
          curr = curr[parts[i]];
        }
        curr[parts[parts.length - 1]] = val;
      };

      if (editFormData.bl_number !== undefined) setNested(updatedJson, "document_metadata.bl_number", editFormData.bl_number || null);
      if (editFormData.bl_date !== undefined) setNested(updatedJson, "document_metadata.bl_date", editFormData.bl_date || null);
      if (editFormData.bl_type !== undefined) setNested(updatedJson, "document_metadata.bl_type", editFormData.bl_type || null);
      if (editFormData.shipper_name !== undefined) setNested(updatedJson, "parties.shipper.name", editFormData.shipper_name || null);
      if (editFormData.shipper_address !== undefined) setNested(updatedJson, "parties.shipper.address", editFormData.shipper_address || null);
      if (editFormData.consignee_name !== undefined) setNested(updatedJson, "parties.consignee.name", editFormData.consignee_name || null);
      if (editFormData.consignee_address !== undefined) setNested(updatedJson, "parties.consignee.address", editFormData.consignee_address || null);
      if (editFormData.notify_party_name !== undefined) setNested(updatedJson, "parties.notify_party.name", editFormData.notify_party_name || null);
      if (editFormData.carrier !== undefined) setNested(updatedJson, "shipment.carrier", editFormData.carrier || null);
      if (editFormData.vessel_name !== undefined) setNested(updatedJson, "shipment.vessel_name", editFormData.vessel_name || null);
      if (editFormData.voyage_number !== undefined) setNested(updatedJson, "shipment.voyage_number", editFormData.voyage_number || null);
      if (editFormData.port_of_loading !== undefined) setNested(updatedJson, "shipment.port_of_loading", editFormData.port_of_loading || null);
      if (editFormData.port_of_discharge !== undefined) setNested(updatedJson, "shipment.port_of_discharge", editFormData.port_of_discharge || null);
      if (editFormData.place_of_delivery !== undefined) setNested(updatedJson, "shipment.place_of_delivery", editFormData.place_of_delivery || null);
      if (editFormData.on_board_date !== undefined) setNested(updatedJson, "dates.on_board_date", editFormData.on_board_date || null);
      if (editFormData.description !== undefined) setNested(updatedJson, "cargo.description", editFormData.description || null);
      if (editFormData.hs_code !== undefined) setNested(updatedJson, "cargo.hs_code", editFormData.hs_code || null);
      if (editFormData.freight_terms !== undefined) setNested(updatedJson, "freight.terms", editFormData.freight_terms || null);
      if (editFormData.currency !== undefined) setNested(updatedJson, "freight.currency", editFormData.currency || null);
      if (editFormData.booking_number !== undefined) setNested(updatedJson, "shipment.booking_number", editFormData.booking_number || null);
      if (editFormData.invoice_number !== undefined) setNested(updatedJson, "references.invoice_number", editFormData.invoice_number || null);

      const res = await api.documents.updateExtraction(documentId, updatedJson);
      setIsEditing(false);
      if (onExtractionUpdated) {
        onExtractionUpdated(res);
      }
    } catch {
      alert("Failed to save updated extraction data.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(rawData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(rawData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `extraction_${documentId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadCsv = () => {
    const getVal = (paths: string[], evKeys: string[]) => getField(paths, evKeys)?.value || "";
    const getConf = (paths: string[], evKeys: string[]) => getField(paths, evKeys)?.confidence || "";
    const getSrc = (paths: string[], evKeys: string[]) => getField(paths, evKeys)?.source_text || "";

    const rows = [
      ["Field", "Value", "Confidence", "Source Snippet"],
      ["B/L Number", getVal(["document_metadata.bl_number", "bl_number"], ["bl_number"]), getConf(["document_metadata.bl_number", "bl_number"], ["bl_number"]), getSrc(["document_metadata.bl_number", "bl_number"], ["bl_number"])],
      ["B/L Date", getVal(["document_metadata.bl_date", "bl_date"], ["bl_date"]), getConf(["document_metadata.bl_date", "bl_date"], ["bl_date"]), getSrc(["document_metadata.bl_date", "bl_date"], ["bl_date"])],
      ["B/L Type", getVal(["document_metadata.bl_type", "bl_type"], ["bl_type"]), getConf(["document_metadata.bl_type", "bl_type"], ["bl_type"]), ""],
      ["Shipper Name", getVal(["parties.shipper.name", "shipper.name"], ["shipper_name"]), getConf(["parties.shipper.name", "shipper.name"], ["shipper_name"]), ""],
      ["Shipper Address", getVal(["parties.shipper.address", "shipper.address"], ["shipper_address"]), getConf(["parties.shipper.address", "shipper.address"], ["shipper_address"]), ""],
      ["Consignee Name", getVal(["parties.consignee.name", "consignee.name"], ["consignee_name"]), getConf(["parties.consignee.name", "consignee.name"], ["consignee_name"]), ""],
      ["Carrier", getVal(["shipment.carrier", "carrier"], ["carrier"]), getConf(["shipment.carrier", "carrier"], ["carrier"]), ""],
      ["Vessel Name", getVal(["shipment.vessel_name", "vessel_name"], ["vessel_name"]), getConf(["shipment.vessel_name", "vessel_name"], ["vessel_name"]), ""],
      ["Voyage Number", getVal(["shipment.voyage_number", "voyage_number"], ["voyage_number"]), getConf(["shipment.voyage_number", "voyage_number"], ["voyage_number"]), ""],
      ["Port of Loading", getVal(["shipment.port_of_loading", "port_of_loading"], ["port_of_loading"]), getConf(["shipment.port_of_loading", "port_of_loading"], ["port_of_loading"]), ""],
      ["Port of Discharge", getVal(["shipment.port_of_discharge", "port_of_discharge"], ["port_of_discharge"]), getConf(["shipment.port_of_discharge", "port_of_discharge"], ["port_of_discharge"]), ""],
      ["Gross Weight", getVal(["cargo.gross_weight", "gross_weight"], ["gross_weight"]), getConf(["cargo.gross_weight", "gross_weight"], ["gross_weight"]), ""],
      ["Cargo Description", getVal(["cargo.description", "description"], ["cargo_description"]), getConf(["cargo.description", "description"], ["cargo_description"]), ""],
      ["Freight Terms", getVal(["freight.terms", "freight_terms"], ["freight_terms"]), getConf(["freight.terms", "freight_terms"], ["freight_terms"]), ""],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `extraction_${documentId.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderField = (
    label: string,
    paths: string[],
    evidenceKeys: string[] = [],
    editKey?: string
  ) => {
    const field = getField(paths, evidenceKeys);
    const formKey = editKey || (paths[0] ? paths[0].replace(/\./g, "_") : label);

    if (isEditing) {
      return (
        <div className="py-2.5 flex flex-col gap-1 border-b border-slate-100 dark:border-slate-800/60">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            {label}
          </label>
          <input
            type="text"
            value={editFormData[formKey] ?? (field?.value ? String(field.value) : "")}
            onChange={(e) =>
              setEditFormData((prev) => ({ ...prev, [formKey]: e.target.value }))
            }
            className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>
      );
    }

    if (!field || field.value === null || field.value === undefined || field.value === "") {
      return (
        <div className="py-2.5 flex justify-between items-center text-xs border-b border-slate-100 dark:border-slate-800/60">
          <span className="text-slate-500 dark:text-slate-400 font-medium">{label}</span>
          <span className="text-slate-300 dark:text-slate-600 italic">Not extracted</span>
        </div>
      );
    }

    const conf = field.confidence ?? 0.85;

    return (
      <div className="py-2.5 flex flex-col gap-1 border-b border-slate-100 dark:border-slate-800/60 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-800/20 px-2 rounded-lg -mx-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500 dark:text-slate-400 font-medium">
            {label}
          </span>
          <div className="flex items-center gap-1.5">
            {field.page !== undefined && field.page !== null && (
              <span className="text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-800 px-1 rounded">p.{field.page}</span>
            )}
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                conf >= 0.8
                  ? "bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40"
                  : conf >= 0.6
                  ? "bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40"
                  : "bg-rose-50 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/40"
              }`}
            >
              {formatConfidence(conf)}
            </span>
          </div>
        </div>
        <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-snug break-words">
          {String(field.value)}
        </div>
        {field.source_text && (
          <div className="text-[10px] text-slate-500 dark:text-slate-400 italic bg-slate-50 dark:bg-slate-800/40 p-1.5 rounded-md font-mono border border-slate-200/50 dark:border-slate-800/40 mt-0.5 break-words">
            &quot;{field.source_text}&quot;
          </div>
        )}
      </div>
    );
  };

  const containersList = Array.isArray(rawData.containers) ? rawData.containers : [];
  const dangerousGoods = rawData.dangerous_goods;

  return (
    <div className="space-y-6">
      {/* Schema Status Header & Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {formatDocType(documentType || "bill_of_lading")} Extraction
              </h4>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900/40">
                v{extraction.schema_version || "2.0"}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Status: <span className="font-semibold text-slate-700 dark:text-slate-300">{(extraction.validation_status ?? "pending").toUpperCase()}</span>
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {isEditing ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsEditing(false)}
                disabled={isSaving}
                className="text-xs"
              >
                <X className="w-3.5 h-3.5 mr-1.5" />
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEdit}
                disabled={isSaving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs shadow-sm shadow-emerald-500/20"
              >
                <Save className="w-3.5 h-3.5 mr-1.5" />
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            </>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleStartEdit}
                className="text-xs"
              >
                <Edit3 className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
                Edit Fields
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCopyJson}
                className="text-xs"
              >
                {copied ? <Check className="w-3.5 h-3.5 mr-1.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5 mr-1.5 text-slate-500" />}
                {copied ? "Copied" : "JSON"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleDownloadCsv}
                className="text-xs"
              >
                <Download className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
                CSV
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  try {
                    setIsReprocessing(true);
                    const res = await api.documents.reprocess(documentId);
                    if (onExtractionUpdated) onExtractionUpdated(res);
                  } catch {
                    alert("Failed to reprocess document.");
                  } finally {
                    setIsReprocessing(false);
                  }
                }}
                disabled={isReprocessing}
                className="text-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-slate-500 ${isReprocessing ? "animate-spin" : ""}`} />
                {isReprocessing ? "Processing..." : "Re-extract"}
              </Button>
            </>
          )}

          {extraction.confidence_score !== null && extraction.confidence_score !== undefined && (
            <div className="hidden lg:flex items-center gap-2 pl-3 ml-2 border-l border-slate-200 dark:border-slate-800">
              <span className="text-xs text-slate-400">Confidence:</span>
              <span className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400">
                {formatConfidence(extraction.confidence_score)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Structured Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Section 1: Document Information */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <FileText className="w-4 h-4 text-blue-500" />
            Document Information
          </div>
          {renderField("B/L Number", ["document_metadata.bl_number", "bl_number"], ["bl_number"], "bl_number")}
          {renderField("B/L Date", ["document_metadata.bl_date", "bl_date", "issue_date", "dates.bl_date", "dates.issue_date"], ["bl_date", "issue_date"], "bl_date")}
          {renderField("B/L Type", ["document_metadata.bl_type", "bl_type"], ["bl_type"], "bl_type")}
          {renderField("B/L Status", ["document_metadata.bl_status", "bl_status"], ["bl_status"], "bl_status")}
          {renderField("Place of Issue", ["document_metadata.place_of_issue", "place_of_issue"], ["place_of_issue"], "place_of_issue")}
          {renderField("Original Copies", ["document_metadata.original_copies", "original_copies"], ["original_copies"], "original_copies")}
        </div>

        {/* Section 2: Parties */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <UserCheck className="w-4 h-4 text-indigo-500" />
            Parties
          </div>
          {renderField("Shipper Name", ["parties.shipper.name", "shipper.name", "shipper"], ["shipper_name", "shipper.name"], "shipper_name")}
          {renderField("Shipper Address", ["parties.shipper.address", "shipper.address"], ["shipper_address", "shipper.address"], "shipper_address")}
          {renderField("Consignee Name", ["parties.consignee.name", "consignee.name", "consignee"], ["consignee_name", "consignee.name"], "consignee_name")}
          {renderField("Consignee Address", ["parties.consignee.address", "consignee.address"], ["consignee_address", "consignee.address"], "consignee_address")}
          {renderField("Notify Party Name", ["parties.notify_party.name", "notify_party.name", "notify_party"], ["notify_party_name", "notify_party.name"], "notify_party_name")}
          {renderField("Notify Party Address", ["parties.notify_party.address", "notify_party.address"], ["notify_party_address", "notify_party.address"], "notify_party_address")}
        </div>

        {/* Section 3: Shipment */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <Ship className="w-4 h-4 text-cyan-500" />
            Shipment
          </div>
          {renderField("Carrier", ["shipment.carrier", "carrier", "shipment.shipping_line", "shipping_line"], ["carrier", "shipping_line"], "carrier")}
          {renderField("Vessel Name", ["shipment.vessel_name", "vessel_name"], ["vessel_name"], "vessel_name")}
          {renderField("Voyage Number", ["shipment.voyage_number", "voyage_number"], ["voyage_number"], "voyage_number")}
          {renderField("Place of Receipt", ["shipment.place_of_receipt", "place_of_receipt"], ["place_of_receipt"], "place_of_receipt")}
          {renderField("Port of Loading (POL)", ["shipment.port_of_loading", "port_of_loading"], ["port_of_loading"], "port_of_loading")}
          {renderField("Port of Discharge (POD)", ["shipment.port_of_discharge", "port_of_discharge"], ["port_of_discharge"], "port_of_discharge")}
          {renderField("Place of Delivery", ["shipment.place_of_delivery", "place_of_delivery", "final_destination"], ["place_of_delivery", "final_destination"], "place_of_delivery")}
        </div>

        {/* Section 4: Dates */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <Calendar className="w-4 h-4 text-rose-500" />
            Dates
          </div>
          {renderField("On Board Date", ["dates.on_board_date", "on_board_date"], ["on_board_date"], "on_board_date")}
          {renderField("Issue Date", ["document_metadata.bl_date", "bl_date", "dates.issue_date", "dates.bl_date"], ["bl_date", "issue_date"], "bl_date")}
        </div>

        {/* Section 5: Cargo */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <Package className="w-4 h-4 text-amber-500" />
            Cargo
          </div>
          {renderField("Cargo Description", ["cargo.description", "description", "cargo.commodity", "commodity"], ["cargo_description", "description"], "description")}
          {renderField("HS Code", ["cargo.hs_code", "hs_code"], ["hs_code"], "hs_code")}
          {renderField("Marks & Numbers", ["cargo.marks_and_numbers", "marks_and_numbers"], ["marks_and_numbers"], "marks_and_numbers")}
          {renderField("Number of Packages", ["cargo.number_of_packages", "number_of_packages", "cargo.package_type"], ["number_of_packages"], "number_of_packages")}
          {renderField("Gross Weight", ["cargo.gross_weight", "gross_weight"], ["gross_weight"], "gross_weight")}
          {renderField("Net Weight", ["cargo.net_weight", "net_weight"], ["net_weight"], "net_weight")}
          {renderField("CBM / Volume", ["cargo.cbm", "cbm", "cargo.volume", "volume"], ["cbm", "volume"], "cbm")}
        </div>

        {/* Section 6 & 7: Freight & References */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
              <DollarSign className="w-4 h-4 text-emerald-500" />
              Freight
            </div>
            {renderField("Freight Terms", ["freight.terms", "freight_terms"], ["freight_terms"], "freight_terms")}
            {renderField("Freight Amount", ["freight.amount", "freight_amount", "prepaid_amount", "collect_amount"], ["freight_amount"], "freight_amount")}
            {renderField("Currency", ["freight.currency", "freight_currency", "currency"], ["currency", "freight_currency"], "currency")}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
              <Info className="w-4 h-4 text-purple-500" />
              References
            </div>
            {renderField("Booking Number", ["shipment.booking_number", "booking_number"], ["booking_number"], "booking_number")}
            {renderField("Invoice Number", ["references.invoice_number", "invoice_number"], ["invoice_number"], "invoice_number")}
            {renderField("Purchase Order No.", ["references.purchase_order_number", "purchase_order_number"], ["purchase_order_number"], "purchase_order_number")}
          </div>
        </div>
      </div>

      {/* Section 8: Containers Table */}
      {containersList.length > 0 && (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-slate-100 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-bold text-sm">
            <Container className="w-4 h-4 text-blue-500" />
            Containers ({containersList.length})
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold">
                  <th className="pb-2.5 pl-2 font-semibold">Container Number</th>
                  <th className="pb-2.5 font-semibold">Seal Number</th>
                  <th className="pb-2.5 font-semibold">Container Type</th>
                  <th className="pb-2.5 pr-2 font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {containersList.map((cntr: any, idx: number) => {
                  const num = cntr.container_number?.value || cntr.container_number || "-";
                  const seal = cntr.seal_number?.value || cntr.seal_number || "-";
                  const type = cntr.container_type?.value || cntr.container_size?.value || cntr.container_type || "-";
                  const conf = cntr.container_number?.confidence ?? extraction.confidence_score ?? 0.95;

                  return (
                    <tr key={idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 pl-2 font-mono font-bold text-blue-600 dark:text-blue-400">
                        {num}
                      </td>
                      <td className="py-3 font-mono text-slate-700 dark:text-slate-300">
                        {seal}
                      </td>
                      <td className="py-3 text-slate-600 dark:text-slate-300">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[11px] font-medium">
                          {type}
                        </span>
                      </td>
                      <td className="py-3 pr-2">
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                          {formatConfidence(conf)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Dangerous Goods Banner if detected */}
      {dangerousGoods && (dangerousGoods.un_number?.value || dangerousGoods.imo_class?.value || dangerousGoods.un_number || dangerousGoods.imo_class) && (
        <div className="rounded-2xl border border-amber-300 dark:border-amber-900/60 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/20 p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500 text-white flex-shrink-0 shadow-md shadow-amber-500/30">
              <Flame className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                IMDG Dangerous Goods Detected
              </h4>
              <p className="text-xs text-amber-700 dark:text-amber-300/90 mt-0.5">
                This shipment contains hazardous cargo regulated under the International Maritime Dangerous Goods Code.
              </p>
              <div className="mt-3 flex flex-wrap gap-4 text-xs font-mono">
                {(dangerousGoods.un_number?.value || dangerousGoods.un_number) && (
                  <div className="bg-amber-100/80 dark:bg-amber-900/50 px-3 py-1.5 rounded-lg border border-amber-300 dark:border-amber-800 font-bold text-amber-900 dark:text-amber-200">
                    UN NUMBER: {dangerousGoods.un_number?.value || dangerousGoods.un_number}
                  </div>
                )}
                {(dangerousGoods.imo_class?.value || dangerousGoods.imo_class) && (
                  <div className="bg-amber-100/80 dark:bg-amber-900/50 px-3 py-1.5 rounded-lg border border-amber-300 dark:border-amber-800 font-bold text-amber-900 dark:text-amber-200">
                    IMO CLASS: {dangerousGoods.imo_class?.value || dangerousGoods.imo_class}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
