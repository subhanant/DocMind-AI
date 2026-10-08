"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  /** Optional label rendered above the control. */
  label?: string;
  placeholder?: string;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  size?: "sm" | "md";
}

/**
 * A styled native `<select>` — keeps full keyboard/screen-reader behaviour and
 * mobile OS pickers while matching the rest of the form controls.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    { className, label, placeholder, options, size = "md", id, ...props },
    ref
  ) => {
    const generatedId = React.useId();
    const selectId = id ?? generatedId;

    const control = (
      <div className="relative w-full">
        <select
          ref={ref}
          id={selectId}
          className={cn(
            "focus-ring w-full cursor-pointer appearance-none rounded-xl border border-line bg-surface text-ink shadow-card transition-[border-color,box-shadow] duration-150 hover:border-line-strong disabled:cursor-not-allowed disabled:opacity-60",
            size === "sm" ? "h-8 py-0 pr-8 pl-2.5 text-xs" : "h-10 pr-9 pl-3 text-sm",
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled={props.required}>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden
          className={cn(
            "pointer-events-none absolute top-1/2 -translate-y-1/2 text-ink-subtle",
            size === "sm" ? "right-2 size-3.5" : "right-3 size-4"
          )}
        />
      </div>
    );

    if (!label) return control;

    return (
      <div className="space-y-1.5">
        <label
          htmlFor={selectId}
          className="text-xs font-semibold uppercase tracking-wide text-ink-subtle"
        >
          {label}
        </label>
        {control}
      </div>
    );
  }
);
Select.displayName = "Select";
