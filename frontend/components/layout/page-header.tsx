import * as React from "react";
import { cn } from "@/lib/utils";
import { DrawRule, MaskReveal, motionVars } from "@/components/motion/reveal";
import { DecodeText } from "@/components/motion/decode-text";

interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;
  /** Optional eyebrow label above the title (e.g. a breadcrumb). */
  eyebrow?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

/** Consistent page title block for every dashboard route. */
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        className
      )}
    >
      <div className="min-w-0">
        {eyebrow && typeof eyebrow === "string" && (
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
            {/* DECODE is reserved for short uppercase labels like this one. */}
            <DecodeText text={eyebrow} startDelay={80} duration={420} />
          </div>
        )}
        {eyebrow && typeof eyebrow !== "string" && (
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
            {eyebrow}
          </div>
        )}

        {/* MASK: the page title rises out of its clipping container. */}
        <MaskReveal
          as="h1"
          className="text-2xl font-bold tracking-tight text-ink sm:text-[28px]"
        >
          {title}
        </MaskReveal>

        {/* DRAW: a short accent rule that grows out from the title. */}
        <DrawRule
          className="mt-3 h-0.5 w-12 rounded-full bg-gradient-to-r from-brand-500 to-brand-500/20"
          delay={180}
        />

        {description && (
          <p
            className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted motion-settle"
            style={motionVars({ index: 1, duration: "0.6s" })}
          >
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  );
}
