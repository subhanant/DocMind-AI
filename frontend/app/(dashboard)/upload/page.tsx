import React from "react";
import { UploadDropzone } from "@/components/upload/dropzone";

export default function UploadPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Upload Documents
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Upload Bills of Lading, Invoices, Packing Lists, or other trade documents for automated processing.
        </p>
      </div>

      <UploadDropzone />
    </div>
  );
}
