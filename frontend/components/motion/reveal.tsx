import * as React from "react";
import { cn } from "@/lib/utils";

/*
 * Motion primitives.
 *
 * These are deliberately hook-free and CSS-driven: the browser runs the
 * entrance on the compositor, React never re-renders for it, and the
 * components can be used from server components too. Only `DecodeText` and
 * `PageTransition` need client-side JS.
 *
 * Vocabulary:
 *   SETTLE — rise a few px + fade (cards, panels, buttons, nav rows)
 *   MASK   — text rises out of a clipping container (headings, result titles)
 *   DRAW   — a rule or border sweeps out from its origin (separators)
 *
 * Every animation ends at `transform: none`, so no element is left with a
 * permanent transform (which would create a containing block and break
 * `position: fixed` descendants).
 *
 * Reduced motion is handled entirely in CSS (see globals.css) — these classes
 * self-disable under `prefers-reduced-motion: reduce`.
 */

/** Inline CSS variables consumed by the motion utilities. */
export function motionVars(options?: {
  /** Position in a stagger sequence (multiplied by `--motion-stagger`). */
  index?: number;
  /** Extra delay in ms, added on top of the stagger offset. */
  delay?: number;
  /** Override the animation duration (e.g. `"0.45s"`). */
  duration?: string;
}): React.CSSProperties {
  if (!options) return {};
  const { index, delay, duration } = options;
  const vars: Record<string, string | number> = {};
  if (index !== undefined) vars["--motion-index"] = index;
  if (delay !== undefined) vars["--motion-delay"] = `${delay}ms`;
  if (duration !== undefined) vars["--motion-duration"] = duration;
  return vars as React.CSSProperties;
}

/** Class name for a settle entrance, for use on elements we cannot wrap (e.g. `<tr>`). */
export function settleClass(options?: {
  index?: number;
  className?: string;
}): string {
  return cn("motion-settle", options?.className);
}

type RevealTag =
  | "div"
  | "section"
  | "span"
  | "li"
  | "header"
  | "footer"
  | "article"
  | "aside"
  | "form"
  | "ul"
  | "ol"
  | "nav"
  | "main";

interface RevealProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  className?: string;
  /** Element to render — avoids invalid wrappers (e.g. a `div` inside `ul`). */
  as?: RevealTag;
  /** Position in the stagger sequence. */
  index?: number;
  /** Extra delay in ms on top of the stagger offset. */
  delay?: number;
  /** Animation duration, e.g. `"0.45s"`. */
  duration?: string;
  /** `fade` for dense lists/rows, `settle` (default) for cards and panels. */
  variant?: "settle" | "fade";
}

/**
 * SETTLE wrapper: content starts slightly lower and near-transparent, then
 * rises into position. Apply a sequence with `index` rather than hand-tuned
 * delays so spacing stays consistent and mobile can compress it.
 */
export function Reveal({
  children,
  className,
  as: Tag = "div",
  index,
  delay,
  duration,
  variant = "settle",
  style,
  ...rest
}: RevealProps) {
  return (
    <Tag
      className={cn(variant === "fade" ? "motion-fade" : "motion-settle", className)}
      style={{ ...motionVars({ index, delay, duration }), ...style }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

interface MaskRevealProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  className?: string;
  /** Class applied to the inner (moving) element. */
  innerClassName?: string;
  as?: "h1" | "h2" | "h3" | "h4" | "div" | "span" | "p";
  index?: number;
  delay?: number;
  duration?: string;
}

/**
 * MASK reveal for headings and important result titles.
 *
 * The outer element clips; the inner element starts fully below the clip and
 * rises into place. `padding-bottom` + matching negative margin keeps
 * descenders (g, y, p) from being shaved off by the overflow clip.
 */
export function MaskReveal({
  children,
  className,
  innerClassName,
  as: Tag = "div",
  index,
  delay,
  duration,
  style,
  ...rest
}: MaskRevealProps) {
  return (
    <Tag
      className={cn("overflow-hidden pb-[0.2em] -mb-[0.2em]", className)}
      style={style}
      {...rest}
    >
      <span
        className={cn("block motion-mask", innerClassName)}
        style={motionVars({ index, delay, duration })}
      >
        {children}
      </span>
    </Tag>
  );
}

interface DrawRuleProps {
  className?: string;
  index?: number;
  delay?: number;
  /** Draw from the left (default) or from the top. */
  orientation?: "horizontal" | "vertical";
}

/**
 * DRAW separator: a hairline that sweeps out from its origin instead of
 * appearing all at once. Purely decorative — hidden from assistive tech.
 *
 * `className` must supply the colour (e.g. `bg-line`, or a `bg-gradient-to-r`
 * accent). The base class carries no background so a gradient is never
 * muddied by a solid colour underneath it.
 */
export function DrawRule({
  className = "bg-line",
  index,
  delay,
  orientation = "horizontal",
}: DrawRuleProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "block",
        orientation === "horizontal"
          ? "h-px w-full origin-left motion-draw-x"
          : "w-px origin-top motion-draw-y",
        className
      )}
      style={motionVars({ index, delay, duration: "0.9s" })}
    />
  );
}

/**
 * Scopes a tighter stagger to a subtree (e.g. rows inside one card) so a long
 * list resolves quickly instead of inheriting the page-level cadence.
 */
export function StaggerScope({
  stagger,
  className,
  children,
  style,
  ...rest
}: {
  stagger: string;
  className?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={className}
      style={{ ["--motion-stagger" as string]: stagger, ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}
