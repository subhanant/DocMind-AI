import * as React from "react";
import {
  FileCode2,
  FileImage,
  FileSpreadsheet,
  FileText,
  File as FileIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type FileTone = "pdf" | "image" | "sheet" | "doc" | "generic";

const TONES: Record<FileTone, { icon: React.ElementType; className: string; chip: string }> = {
  pdf: {
    icon: FileText,
    className: "border-rose-200 bg-rose-50 text-rose-600 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400",
    chip: "bg-rose-500",
  },
  image: {
    icon: FileImage,
    className: "border-emerald-200 bg-emerald-50 text-emerald-600 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-400",
    chip: "bg-emerald-500",
  },
  sheet: {
    icon: FileSpreadsheet,
    className: "border-emerald-200 bg-emerald-50 text-emerald-600 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-400",
    chip: "bg-emerald-500",
  },
  doc: {
    icon: FileCode2,
    className: "border-brand-200 bg-brand-50 text-brand-600 dark:border-brand-900/60 dark:bg-brand-950/40 dark:text-brand-300",
    chip: "bg-brand-500",
  },
  generic: {
    icon: FileIcon,
    className: "border-line bg-surface-muted text-ink-subtle",
    chip: "bg-ink-subtle",
  },
};

export function fileTone(fileType: string | null | undefined): FileTone {
  switch ((fileType ?? "").toLowerCase()) {
    case "pdf":
      return "pdf";
    case "png":
    case "jpg":
    case "jpeg":
    case "webp":
    case "gif":
      return "image";
    case "xlsx":
    case "xls":
    case "csv":
      return "sheet";
    case "docx":
    case "doc":
      return "doc";
    default:
      return "generic";
  }
}

export function FileTypeIcon({
  fileType,
  className,
}: {
  fileType: string | null | undefined;
  className?: string;
}) {
  const { icon: Icon, className: tone } = TONES[fileTone(fileType)];
  return (
    <span
      aria-hidden
      className={cn(
        "flex items-center justify-center rounded-xl border",
        "h-9 w-9 [&_svg]:size-4",
        tone,
        className
      )}
    >
      <Icon />
    </span>
  );
}

export function fileTypeChipClass(fileType: string | null | undefined): string {
  return TONES[fileTone(fileType)].chip;
}
