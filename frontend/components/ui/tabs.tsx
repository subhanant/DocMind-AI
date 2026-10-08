"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsContextValue {
  value: string;
  onValueChange: (val: string) => void;
  name: string;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

export function Tabs({
  value,
  defaultValue,
  onValueChange,
  children,
  className,
  name = "tabs",
}: {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
  name?: string;
}) {
  const [tab, setTab] = React.useState(value || defaultValue || "");

  const currentTab = value !== undefined ? value : tab;
  const handleTabChange = React.useCallback(
    (newVal: string) => {
      if (value === undefined) setTab(newVal);
      onValueChange?.(newVal);
    },
    [value, onValueChange]
  );

  return (
    <TabsContext.Provider
      value={{ value: currentTab, onValueChange: handleTabChange, name }}
    >
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className,
  "aria-label": ariaLabel,
}: {
  children: React.ReactNode;
  className?: string;
  "aria-label"?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center gap-1 rounded-xl border border-line bg-surface-muted p-1",
        className
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className,
  disabled,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsTrigger must be used inside Tabs");
  const isActive = ctx.value === value;

  return (
    <button
      type="button"
      role="tab"
      id={`${ctx.name}-tab-${value}`}
      aria-selected={isActive}
      aria-controls={`${ctx.name}-panel-${value}`}
      onClick={() => ctx.onValueChange(value)}
      disabled={disabled}
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition-[background-color,color,box-shadow] duration-150 select-none disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:size-4",
        isActive
          ? "bg-surface text-ink shadow-card"
          : "text-ink-muted hover:bg-surface-hover hover:text-ink",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsContent must be used inside Tabs");
  if (ctx.value !== value) return null;

  return (
    <div
      role="tabpanel"
      id={`${ctx.name}-panel-${value}`}
      aria-labelledby={`${ctx.name}-tab-${value}`}
      tabIndex={0}
      className={cn("mt-5 animate-fade-in focus-ring rounded-xl", className)}
    >
      {children}
    </div>
  );
}
