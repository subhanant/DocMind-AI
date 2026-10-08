"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  /** Render an icon inside the field, on the leading edge. */
  leadingIcon?: React.ReactNode;
  /** Render an actionable element (e.g. password toggle) on the trailing edge. */
  trailingSlot?: React.ReactNode;
  invalid?: boolean;
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, leadingIcon, trailingSlot, invalid, ...props }, ref) => {
    const input = (
      <input
        ref={ref}
        type={type}
        aria-invalid={invalid || undefined}
        className={cn(
          "focus-ring h-10 w-full rounded-xl border bg-surface px-3 text-sm text-ink shadow-card transition-[border-color,box-shadow,background-color] duration-200 ease-[var(--ease-settle)]",
          "placeholder:text-ink-subtle disabled:cursor-not-allowed disabled:opacity-60",
          "file:mr-3 file:rounded-md file:border-0 file:bg-surface-muted file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink",
          invalid
            ? "border-rose-400 focus-visible:outline-rose-500 dark:border-rose-800"
            : "border-line hover:border-line-strong",
          leadingIcon && "pl-9.5",
          trailingSlot && "pr-10",
          className
        )}
        {...props}
      />
    );

    if (!leadingIcon && !trailingSlot) return input;

    return (
      <div className="relative w-full">
        {leadingIcon && (
          <span
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 flex -translate-y-1/2 items-center text-ink-subtle [&_svg]:size-4"
          >
            {leadingIcon}
          </span>
        )}
        {input}
        {trailingSlot && (
          <span className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center">
            {trailingSlot}
          </span>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

interface FieldProps {
  id?: string;
  label: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}

/** Label + hint/error scaffolding that keeps spacing identical across forms. */
export function Field({
  id,
  label,
  hint,
  error,
  required,
  className,
  children,
}: FieldProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label
        htmlFor={id}
        className="flex items-center gap-1 text-xs font-semibold text-ink"
      >
        {label}
        {required && (
          <span className="text-rose-500" aria-hidden>
            *
          </span>
        )}
      </label>
      {children}
      {error ? (
        <p className="text-[11px] font-medium text-rose-600 dark:text-rose-400">{error}</p>
      ) : hint ? (
        <p className="text-[11px] leading-snug text-ink-subtle">{hint}</p>
      ) : null}
    </div>
  );
}

export { Input };
