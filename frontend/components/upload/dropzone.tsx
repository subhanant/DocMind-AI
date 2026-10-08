"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  FileStack,
  Loader2,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import { DocumentType } from "@/types";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Alert } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { FileTypeIcon } from "@/components/documents/file-icon";
import { useToast } from "@/components/ui/toast";
import { cn, formatBytes } from "@/lib/utils";
import { Reveal, motionVars } from "@/components/motion/reveal";
import { ProcessingStrip } from "@/components/motion/processing-strip";

const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "webp", "docx", "xlsx"];
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // matches backend MAX_UPLOAD_SIZE_MB
const MAX_FILES = 10; // matches the backend per-request limit

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface FileWithStatus {
  file: File;
  id: string;
  status: UploadStatus;
  progress: number;
  error?: string;
}

let fileCounter = 0;
const nextFileId = () => `file-${Date.now()}-${fileCounter++}`;

export function UploadDropzone() {
  const router = useRouter();
  const toast = useToast();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);

  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedType, setSelectedType] = useState<DocumentType | "">("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [uploadComplete, setUploadComplete] = useState(false);

  const validateFile = (file: File): string | null => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported type (.${ext ?? "?"}). Allowed: ${ALLOWED_EXTENSIONS.join(", ").toUpperCase()}`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `Exceeds the 50 MB limit (${formatBytes(file.size)})`;
    }
    if (file.size === 0) {
      return "File is empty";
    }
    return null;
  };

  const handleFilesAdded = useCallback((incoming: FileList | File[]) => {
    setGlobalError(null);
    setUploadComplete(false);
    setResultMessage(null);

    const incomingFiles = Array.from(incoming);
    if (incomingFiles.length === 0) return;

    setFiles((prev) => {
      const next = [...prev];
      const existingKeys = new Set(
        prev.map((item) => `${item.file.name}:${item.file.size}`)
      );

      for (const file of incomingFiles) {
        const key = `${file.name}:${file.size}`;
        if (existingKeys.has(key)) continue;
        existingKeys.add(key);

        const error = validateFile(file);
        next.push({
          file,
          id: nextFileId(),
          status: error ? "error" : "idle",
          progress: 0,
          error: error ?? undefined,
        });
      }

      const total = next.length;
      if (total > MAX_FILES) {
        setGlobalError(
          `You can upload at most ${MAX_FILES} files per batch. Extra files were not added.`
        );
        return next.slice(0, MAX_FILES);
      }
      return next;
    });
  }, []);

  const handleDragEnter = (event: React.DragEvent) => {
    event.preventDefault();
    dragDepth.current += 1;
    setIsDragging(true);
  };

  // Only leave the drag state when the pointer exits the outermost boundary —
  // dragleave fires for every child element otherwise, causing flicker.
  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    dragDepth.current = 0;
    setIsDragging(false);
    if (event.dataTransfer.files?.length) {
      handleFilesAdded(event.dataTransfer.files);
    }
  };

  // Paste-to-upload: drop a screenshot straight into the page.
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const pasted = event.clipboardData?.files;
      if (pasted && pasted.length > 0) handleFilesAdded(pasted);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFilesAdded]);

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const pendingCount = files.filter((f) => f.status === "idle").length;
  const validCount = files.filter((f) => f.status !== "error").length;
  const totalBytes = files
    .filter((f) => f.status !== "error")
    .reduce((sum, f) => sum + f.file.size, 0);

  const handleStartUpload = async () => {
    const queued = files.filter((f) => f.status === "idle");
    if (queued.length === 0) return;

    setIsSubmitting(true);
    setGlobalError(null);
    setResultMessage(null);

    setFiles((prev) =>
      prev.map((f) => (f.status === "idle" ? { ...f, status: "uploading", progress: 35 } : f))
    );

    try {
      const res = await api.documents.upload(
        queued.map((f) => f.file),
        selectedType ? selectedType : undefined
      );

      const returned = Array.isArray(res) ? res : [];
      // The API echoes back the primary document only, but every file in a
      // successful request has been accepted and queued for processing.
      setFiles((prev) =>
        prev.map((f) =>
          f.status === "uploading"
            ? { ...f, status: "success", progress: 100 }
            : f
        )
      );
      setUploadComplete(true);

      const message =
        returned.length > 0
          ? `${queued.length} document${queued.length === 1 ? "" : "s"} uploaded and queued for AI extraction.`
          : `${queued.length} document${queued.length === 1 ? "" : "s"} queued for AI extraction.`;
      setResultMessage(message);
      toast.success("Upload complete", message);
    } catch (err: unknown) {
      const message =
        err instanceof ApiError
          ? err.message
          : "The upload could not be completed. Please try again.";
      setGlobalError(message);
      setFiles((prev) =>
        prev.map((f) =>
          f.status === "uploading" ? { ...f, status: "error", error: message, progress: 0 } : f
        )
      );
      toast.error("Upload failed", message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetAll = () => {
    setFiles([]);
    setGlobalError(null);
    setResultMessage(null);
    setUploadComplete(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-6">
      {/* Classification hint */}
      <Card
        className="flex flex-col gap-4 p-5 motion-settle sm:flex-row sm:items-center sm:justify-between"
        style={motionVars({ index: 0 })}
      >
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-ink">Classification hint</h2>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-ink-muted">
            Optionally tell the pipeline which schema to target. Leave it unset and DocMind AI
            will classify each document automatically.
          </p>
        </div>
        <div className="w-full sm:w-64">
          <Select
            size="sm"
            aria-label="Document classification hint"
            value={selectedType}
            onChange={(event) =>
              setSelectedType(event.target.value as DocumentType | "")
            }
            options={[
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
            ]}
            placeholder="Auto-detect"
          />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Dropzone */}
        <div className="lg:col-span-3">
          <Reveal index={1} className="h-full">
            <div
              role="button"
              tabIndex={0}
              aria-label="Drag and drop files here, or press Enter to browse"
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              onDragEnter={handleDragEnter}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                "focus-ring flex h-full min-h-[320px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-[border-color,background-color,transform,box-shadow] duration-200 ease-[var(--ease-settle)]",
                isDragging
                  ? "scale-[1.005] border-brand-500 bg-brand-50/70 shadow-card dark:bg-brand-950/30"
                  : "border-line-strong bg-surface-muted/40 hover:border-brand-400 hover:bg-surface-hover hover:shadow-card"
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(",")}
                className="hidden"
                onChange={(event) => {
                  if (event.target.files?.length) handleFilesAdded(event.target.files);
                  event.target.value = "";
                }}
              />

              <span
                className={cn(
                  "flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-brand transition-transform duration-200 [&_svg]:size-7",
                  isDragging && "scale-110"
                )}
              >
                <UploadCloud />
              </span>

              <p className="mt-5 text-base font-semibold text-ink">
                {isDragging ? "Drop files to add them" : "Drag & drop documents here"}
              </p>
              <p className="mt-1.5 text-sm text-ink-muted">
                or{" "}
                <span className="font-semibold text-brand-600 underline underline-offset-4 dark:text-brand-300">
                  browse your files
                </span>{" "}
                — you can also paste with ⌘V
              </p>

              <ul className="mt-6 flex flex-wrap items-center justify-center gap-1.5">
                {ALLOWED_EXTENSIONS.map((ext) => (
                  <li
                    key={ext}
                    className="rounded-md border border-line bg-surface px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink-subtle"
                  >
                    {ext}
                  </li>
                ))}
              </ul>

              <p className="mt-5 text-[11px] text-ink-subtle">
                Max {MAX_FILES} files per batch · 50 MB per file
              </p>
            </div>
          </Reveal>
        </div>

        {/* Guidance panel */}
        <div className="lg:col-span-2">
          <Card
            className="h-full p-5 motion-settle"
            style={motionVars({ index: 2 })}
          >
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300 [&_svg]:size-4">
                <Sparkles />
              </span>
              <h2 className="text-sm font-semibold text-ink">What happens next</h2>
            </div>

            <ol className="mt-4 space-y-4">
              {[
                {
                  title: "Secure storage",
                  body: "Files are validated by MIME type and stored under an isolated UUID path.",
                },
                {
                  title: "Text & OCR extraction",
                  body: "Digital text layers are read directly; scans fall back to OCR.",
                },
                {
                  title: "Classification",
                  body: "Each document is routed to the matching extraction schema.",
                },
                {
                  title: "Structured extraction",
                  body: "Fields are returned with confidence scores and source evidence.",
                },
              ].map((step, index) => (
                <li
                  key={step.title}
                  className="flex gap-3 motion-fade"
                  style={motionVars({ index: index + 3, duration: "0.45s" })}
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-line bg-surface-muted text-[10px] font-bold text-ink-muted">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-xs font-semibold text-ink">{step.title}</p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">
                      {step.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>

            <div className="mt-5 rounded-xl border border-line bg-surface-muted p-3">
              <p className="text-[11px] leading-relaxed text-ink-muted">
                Processing runs in the background. You can close this page — results appear in{" "}
                <Link href="/documents" className="font-semibold text-brand-600 dark:text-brand-300">
                  Documents
                </Link>{" "}
                and notifications once ready.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {globalError && (
        <Reveal index={0} duration="0.5s">
          <Alert variant="error" title="Upload blocked">
            {globalError}
          </Alert>
        </Reveal>
      )}

      {resultMessage && (
        <Reveal index={0} duration="0.5s">
          <Alert variant="success" title="Upload complete" role="status">
            {resultMessage}
          </Alert>
        </Reveal>
      )}

      {/* Queue */}
      {files.length > 0 && (
        <Card
          className="overflow-hidden motion-settle"
          style={motionVars({ index: 0, duration: "0.55s" })}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
            <div className="flex items-center gap-2.5">
              <FileStack className="h-4 w-4 text-ink-subtle" />
              <h2 className="text-sm font-semibold text-ink">
                Selected files
                <span className="ml-1.5 text-ink-subtle">({files.length})</span>
              </h2>
              {validCount > 0 && (
                <span className="text-xs text-ink-subtle tabular">
                  · {formatBytes(totalBytes)} total
                </span>
              )}
            </div>
            {!isSubmitting && (
              <Button variant="ghost" size="sm" onClick={resetAll} className="text-ink-muted">
                <Trash2 className="h-3.5 w-3.5" />
                Clear all
              </Button>
            )}
          </div>

          <ul className="divide-y divide-line">
            {files.map((item, fileIndex) => (
              <li
                key={item.id}
                className="flex items-center gap-3 px-5 py-3.5 motion-settle"
                style={motionVars({ index: Math.min(fileIndex, 6), duration: "0.45s" })}
              >
                <FileTypeIcon fileType={item.file.name.split(".").pop()} />

                <div className="min-w-0 flex-1">
                  <p
                    className="truncate text-sm font-medium text-ink"
                    title={item.file.name}
                  >
                    {item.file.name}
                  </p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px]">
                    <span className="tabular text-ink-subtle">{formatBytes(item.file.size)}</span>
                    {item.error && (
                      <span className="font-medium text-rose-600 dark:text-rose-400">
                        · {item.error}
                      </span>
                    )}
                  </div>
                  {item.status === "uploading" && (
                    /* Indeterminate: we do not know how long the request takes,
                       so a sweeping hairline reads better than a fake bar. */
                    <ProcessingStrip className="mt-2.5 max-w-xs" />
                  )}
                  {item.status === "success" && (
                    <Progress value={100} className="mt-2 max-w-xs" tone="emerald" />
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {item.status === "uploading" && (
                    <span className="flex items-center gap-1.5 text-xs font-medium text-brand-600 motion-fade dark:text-brand-300">
                      <span
                        aria-hidden
                        className="h-1.5 w-1.5 rounded-full bg-brand-500 motion-tick motion-essential"
                      />
                      Uploading
                    </span>
                  )}
                  {item.status === "success" && (
                    <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Queued
                    </span>
                  )}
                  {item.status === "error" && (
                    <span className="flex items-center gap-1.5 text-xs font-medium text-rose-600 dark:text-rose-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Rejected
                    </span>
                  )}
                  {item.status !== "uploading" && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeFile(item.id)}
                      aria-label={`Remove ${item.file.name}`}
                      className="text-ink-subtle hover:text-rose-600 dark:hover:text-rose-400"
                    >
                      <X />
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          <div className="flex flex-col gap-3 border-t border-line bg-surface-muted/50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between motion-fade" style={motionVars({ duration: "0.5s" })}>
            <p className="text-xs text-ink-muted">
              {pendingCount > 0
                ? `${pendingCount} file${pendingCount === 1 ? "" : "s"} ready to upload`
                : files.some((f) => f.status === "error")
                ? "Remove or replace rejected files to continue"
                : "All selected files have been uploaded"}
            </p>

            <div className="flex flex-wrap items-center gap-2">
              {uploadComplete && (
                /* Completion CTAs settle in once the queue is accepted. */
                <Reveal
                  index={0}
                  duration="0.45s"
                  className="flex flex-wrap items-center gap-2"
                >
                  <Button variant="outline" onClick={resetAll}>
                    Upload more
                  </Button>
                  <Button onClick={() => router.push("/documents")} className="gap-1.5">
                    View in documents
                    <Sparkles className="h-4 w-4" />
                  </Button>
                </Reveal>
              )}
              {!uploadComplete && (
                <Button
                  onClick={handleStartUpload}
                  disabled={isSubmitting || pendingCount === 0}
                  className="gap-1.5"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin motion-essential" />
                      Uploading…
                    </>
                  ) : (
                    <>
                      <UploadCloud className="h-4 w-4" />
                      Upload {pendingCount} file{pendingCount === 1 ? "" : "s"}
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
