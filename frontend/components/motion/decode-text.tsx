"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/*
 * DECODE — a deliberately restrained version of the character-scramble effect.
 *
 * Rules we hold to:
 *   • characters resolve strictly left-to-right
 *   • random characters exist only for a few frames
 *   • the final string is always restored exactly
 *   • width is reserved up-front, so nothing reflows while decoding
 *   • it is never used for paragraphs, extracted values or form fields
 *   • it is fully disabled under `prefers-reduced-motion: reduce`
 *
 * Intended only for short labels: navigation items, uppercase section labels
 * and primary CTA labels.
 */

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

/** Media queries cannot be evaluated on the server. */
const matchesNothing = () => false;

/** SSR-safe media-query subscription that never sets state inside an effect. */
export function useMediaQuery(query: string): boolean {
  const subscribe = React.useCallback(
    (callback: () => void) => {
      const media = window.matchMedia(query);
      media.addEventListener("change", callback);
      return () => media.removeEventListener("change", callback);
    },
    [query]
  );
  const getSnapshot = React.useCallback(
    () => window.matchMedia(query).matches,
    [query]
  );
  return React.useSyncExternalStore(subscribe, getSnapshot, matchesNothing);
}

/** SSR-safe `prefers-reduced-motion` listener (no setState inside an effect). */
export function useReducedMotion(): boolean {
  return useMediaQuery(REDUCED_MOTION_QUERY);
}

const POOLS = {
  lower: "abcdefghijklmnopqrstuvwxyz",
  upper: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
  digit: "0123456789",
};

function randomCharFor(char: string): string {
  // Whitespace and symbols are preserved: it keeps word widths (and therefore
  // the reserved box) stable while the rest of the string is scrambling.
  if (/[\s]/.test(char)) return char;
  if (/[a-z]/.test(char)) return POOLS.lower[Math.floor(Math.random() * 26)];
  if (/[A-Z]/.test(char)) return POOLS.upper[Math.floor(Math.random() * 26)];
  if (/[0-9]/.test(char)) return POOLS.digit[Math.floor(Math.random() * 10)];
  return char;
}

interface DecodeOptions {
  /** Total decode time in ms. */
  duration?: number;
  /** Set to false to keep the plain text (e.g. while a filter is active). */
  enabled?: boolean;
}

/** Touch viewports drop the scramble: short movement, simple entrances. */
const COMPACT_QUERY = "(max-width: 640px)";

export function useDecodeText(text: string, options?: DecodeOptions) {
  const reduced = useReducedMotion();
  const isCompact = useMediaQuery(COMPACT_QUERY);
  const duration = options?.duration ?? 520;
  const enabled = (options?.enabled ?? true) && !reduced && !isCompact;

  const [display, setDisplay] = React.useState(text);
  const frameRef = React.useRef<number | null>(null);

  const cancel = React.useCallback(() => {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  }, []);

  const start = React.useCallback(() => {
    cancel();
    if (!enabled) {
      setDisplay(text);
      return;
    }

    const chars = [...text];
    const resolveWindow = duration * 0.7; // last 30% is already settled
    let startedAt: number | null = null;
    let lastPaint = 0;

    const step = (timestamp: number) => {
      if (startedAt === null) startedAt = timestamp;
      const elapsed = timestamp - startedAt;

      // Paint ~25fps instead of every frame: a 520ms decode is ~13 renders.
      if (elapsed - lastPaint >= 40 || elapsed >= duration) {
        lastPaint = elapsed;
        let next = "";
        for (let i = 0; i < chars.length; i++) {
          const resolveAt = ((i + 1) / chars.length) * resolveWindow;
          next += elapsed >= resolveAt ? chars[i] : randomCharFor(chars[i]);
        }
        setDisplay(next === text ? text : next);
      }

      if (elapsed >= duration) {
        setDisplay(text);
        frameRef.current = null;
        return;
      }
      frameRef.current = requestAnimationFrame(step);
    };

    frameRef.current = requestAnimationFrame(step);
  }, [cancel, enabled, text, duration]);

  // Stop any in-flight loop on unmount.
  React.useEffect(() => cancel, [cancel]);

  return { display, start, reduced, isCompact };
}

interface DecodeTextProps {
  text: string;
  className?: string;
  /** `mount` runs once on entry, `hover` replays on pointer/focus. */
  trigger?: "mount" | "hover";
  duration?: number;
  startDelay?: number;
  enabled?: boolean;
}

export function DecodeText({
  text,
  className,
  trigger = "mount",
  duration,
  startDelay = 0,
  enabled = true,
}: DecodeTextProps) {
  const { display, start } = useDecodeText(text, { duration, enabled });

  // `start` is re-created whenever `text` changes, so a label that swaps its
  // copy re-decodes instead of holding a stale string.
  React.useEffect(() => {
    if (trigger !== "mount") return;
    const timer = setTimeout(start, startDelay);
    return () => clearTimeout(timer);
  }, [trigger, startDelay, start, text]);

  const hoverProps =
    trigger === "hover"
      ? {
          onMouseEnter: start,
          onFocus: start,
        }
      : {};

  return (
    <span
      className={cn("relative inline-block whitespace-nowrap", className)}
      {...hoverProps}
    >
      {/* Accessible name — the animated copy below is aria-hidden. */}
      <span className="sr-only">{text}</span>
      {/* Reserves the exact final width so decoding never shifts layout. */}
      <span aria-hidden className="invisible">
        {text}
      </span>
      <span aria-hidden className="absolute inset-0">
        {display}
      </span>
    </span>
  );
}
