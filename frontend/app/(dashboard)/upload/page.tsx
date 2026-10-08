import React from "react";
import { PageHeader } from "@/components/layout/page-header";
import { UploadDropzone } from "@/components/upload/dropzone";

export const metadata = {
  title: "Upload documents",
};

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Ingest"
        title="Upload documents"
        description="Add Bills of Lading, commercial invoices, packing lists or any supported trade document. DocMind AI classifies each file and extracts structured fields automatically."
      />
      <UploadDropzone />
    </div>
  );
}
