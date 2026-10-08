import * as React from "react";
import Link from "next/link";
import { FileSearch, Gauge, Quote, Sparkles } from "lucide-react";

const HIGHLIGHTS = [
  {
    icon: FileSearch,
    title: "Structured extraction",
    body: "Bills of lading, invoices and packing lists are parsed into typed fields.",
  },
  {
    icon: Gauge,
    title: "Confidence you can audit",
    body: "Every value carries a confidence score and the source text it came from.",
  },
  {
    icon: Quote,
    title: "Evidence-backed results",
    body: "Jump from a field straight to the sentence the model read it from.",
  },
];

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-canvas">
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden bg-slate-950 lg:flex lg:w-1/2 lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(120%_120%_at_0%_0%,#312e81_0%,#0b1120_55%,#070a13_100%)]"
        />
        <div
          aria-hidden
          className="grid-pattern absolute inset-0 text-white/70 opacity-[0.07]"
        />
        <div
          aria-hidden
          className="absolute -right-24 top-1/3 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl"
        />

        <div className="relative p-10">
          <Link href="/login" className="focus-ring inline-flex items-center gap-3 rounded-xl">
            <span className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-500 via-brand-600 to-cyan-500 text-white shadow-brand">
              <Sparkles className="h-5 w-5" />
              <span className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/25" />
            </span>
            <span className="flex items-baseline gap-1">
              <span className="text-lg font-bold tracking-tight text-white">DocMind</span>
              <span className="rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-brand-200">
                AI
              </span>
            </span>
          </Link>
        </div>

        <div className="relative px-10">
          <h2 className="max-w-md text-3xl font-bold leading-tight tracking-tight text-white">
            Document intelligence,{" "}
            <span className="text-gradient">extracted in seconds</span>
          </h2>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300/90">
            Upload trade documents and get structured, validated, confidence-scored data back —
            ready for your systems.
          </p>

          <ul className="mt-10 space-y-6">
            {HIGHLIGHTS.map((highlight) => (
              <li key={highlight.title} className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-brand-200 [&_svg]:size-5">
                  <highlight.icon />
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{highlight.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">
                    {highlight.body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative p-10">
          <div className="flex flex-wrap items-center gap-1.5">
            {["Upload", "OCR", "Classify", "Extract", "Validate"].map((stage, index, all) => (
              <React.Fragment key={stage}>
                <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-300">
                  {stage}
                </span>
                {index < all.length - 1 && (
                  <span aria-hidden className="text-xs text-slate-600">
                    →
                  </span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full items-center justify-center px-4 py-10 sm:px-8 lg:w-1/2">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-500 via-brand-600 to-cyan-500 text-white shadow-brand">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="flex items-baseline gap-1">
              <span className="text-lg font-bold tracking-tight text-ink">DocMind</span>
              <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
                AI
              </span>
            </span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">{subtitle}</p>

          <div className="mt-8 rounded-2xl border border-line bg-surface p-6 shadow-card sm:p-8">
            {children}
          </div>

          <div className="mt-6 text-center text-sm text-ink-muted">{footer}</div>
        </div>
      </div>
    </div>
  );
}
