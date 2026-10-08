"use client";

import React, { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  FileCheck,
  FileSpreadsheet,
  FileCode,
  X,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ArrowRight,
} from "lucide-react";
import { DocumentType, DocumentItem } from "@/types";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/utils";

const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "docx", "xlsx"];
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

interface FileWithStatus {
  file: File;
  id: string;
  status: "idle" | "uploading" | "success" | "error";
  progress: number;
  error?: string;
  uploadedDoc?: DocumentItem;
}

export function UploadDropzone() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedType, setSelectedType] = useState<DocumentType | "">("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [uploadComplete, setUploadComplete] = useState(false);

  const validateFile = (file: File): string | null => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type (.${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(", ").toUpperCase()}`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File exceeds maximum limit of 50MB (${formatBytes(file.size)})`;
    }
    return null;
  };

  const handleFilesAdded = useCallback((newFiles: FileList | File[]) => {
    setGlobalError(null);
    setUploadComplete(false);

    const added: FileWithStatus[] = [];
    Array.from(newFiles).forEach((file) => {
      const error = validateFile(file);
      added.push({
        file,
        id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
        status: error ? "error" : "idle",
        progress: 0,
        error: error || undefined,
      });
    });

    setFiles((prev) => [...prev, ...added]);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleStartUpload = async () => {
    const validFiles = files.filter((f) => f.status === "idle");
    if (validFiles.length === 0) return;

    setIsSubmitting(true);
    setGlobalError(null);

    // Update status to uploading
    setFiles((prev) =>
      prev.map((f) =>
        f.status === "idle" ? { ...f, status: "uploading", progress: 50 } : f
      )
    );

    try {
      const rawFiles = validFiles.map((f) => f.file);
      const docs = await api.documents.upload(
        rawFiles,
        selectedType ? selectedType : undefined
      );

      // Map results back
      setFiles((prev) =>
        prev.map((f) => {
          const match = docs.find((d) => d.original_filename === f.file.name);
          if (match) {
            return {
              ...f,
              status: "success",
              progress: 100,
              uploadedDoc: match,
            };
          }
          return f;
        })
      );

      setUploadComplete(true);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Upload failed";
      setGlobalError(msg);
      setFiles((prev) =>
        prev.map((f) =>
          f.status === "uploading"
            ? { ...f, status: "error", error: msg, progress: 0 }
            : f
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "pdf":
        return <FileText className="w-5 h-5 text-rose-500" />;
      case "xlsx":
      case "xls":
        return <FileSpreadsheet className="w-5 h-5 text-emerald-500" />;
      case "docx":
      case "doc":
        return <FileCode className="w-5 h-5 text-blue-500" />;
      default:
        return <FileCheck className="w-5 h-5 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Settings / Classification Hint */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Document Classification (Optional)
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Select a target schema or allow the pipeline to auto-classify.
          </p>
        </div>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value as DocumentType | "")}
          className="h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Auto-Detect / Unknown (Phase 1)</option>
          <option value="bill_of_lading">Bill of Lading (B/L)</option>
          <option value="commercial_invoice">Commercial Invoice</option>
          <option value="packing_list">Packing List</option>
          <option value="purchase_order">Purchase Order</option>
          <option value="certificate_of_origin">Certificate of Origin</option>
          <option value="delivery_challan">Delivery Challan</option>
          <option value="customs_document">Customs Document</option>
          <option value="shipping_document">Shipping Document</option>
          <option value="contract">Contract</option>
          <option value="receipt">Receipt</option>
        </select>
      </div>

      {/* Drag & Drop Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-10 sm:p-14 border-2 border-dashed rounded-2xl cursor-pointer transition-all ${
          isDragging
            ? "border-blue-500 bg-blue-50/60 dark:bg-blue-950/30 scale-[1.005]"
            : "border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50 hover:bg-slate-50 dark:hover:bg-slate-900 hover:border-slate-400 dark:hover:border-slate-600"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.docx,.xlsx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFilesAdded(e.target.files);
            }
          }}
        />

        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600/10 text-blue-600 dark:text-blue-400 mb-4 shadow-inner">
          <UploadCloud className="h-7 w-7" />
        </div>

        <h3 className="text-base font-semibold text-slate-900 dark:text-white text-center">
          Drag & drop your documents here, or{" "}
          <span className="text-blue-600 dark:text-blue-400 underline underline-offset-4">
            browse
          </span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 text-center mt-1.5 max-w-sm">
          Supports multiple uploads. Maximum file size: 50MB per file.
        </p>

        {/* Supported badges */}
        <div className="flex flex-wrap items-center justify-center gap-1.5 mt-5">
          {["PDF", "JPG", "JPEG", "PNG", "DOCX", "XLSX"].map((ext) => (
            <span
              key={ext}
              className="px-2 py-0.5 text-[10px] font-semibold tracking-wide rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 shadow-2xs"
            >
              {ext}
            </span>
          ))}
        </div>
      </div>

      {/* Global Error Banner */}
      {globalError && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{globalError}</span>
        </div>
      )}

      {/* File Queue List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Selected Files ({files.length})
            </h4>
            {!isSubmitting && (
              <button
                onClick={() => setFiles([])}
                className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
            {files.map((item) => (
              <div
                key={item.id}
                className="p-3.5 flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-9 w-9 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
                    {getFileIcon(item.file.name)}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 dark:text-slate-100 truncate max-w-xs sm:max-w-md">
                      {item.file.name}
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span>{formatBytes(item.file.size)}</span>
                      {item.error && (
                        <span className="text-rose-600 dark:text-rose-400 font-medium">
                          • {item.error}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {item.status === "uploading" && (
                    <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400 font-medium">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Uploading...
                    </span>
                  )}
                  {item.status === "success" && (
                    <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Uploaded
                    </span>
                  )}
                  {item.status === "error" && (
                    <span className="text-rose-600 dark:text-rose-400 font-medium">
                      Failed
                    </span>
                  )}
                  {item.status !== "uploading" && (
                    <button
                      onClick={() => removeFile(item.id)}
                      className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Action CTAs */}
          <div className="flex items-center justify-between pt-2">
            <div>
              {uploadComplete && (
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  All valid documents uploaded & registered in database!
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              {uploadComplete ? (
                <Button onClick={() => router.push("/documents")} className="gap-1.5">
                  View in Documents <ArrowRight className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleStartUpload}
                  disabled={
                    isSubmitting ||
                    files.filter((f) => f.status === "idle").length === 0
                  }
                  className="gap-1.5"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing Upload...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      Upload {files.filter((f) => f.status === "idle").length} Document
                      {files.filter((f) => f.status === "idle").length === 1 ? "" : "s"}
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
