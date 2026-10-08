import * as React from "react";
import { cn } from "@/lib/utils";

export function TableWrapper({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "overflow-x-auto overscroll-x-contain [-webkit-overflow-scrolling:touch]",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Table({
  className,
  children,
  ...props
}: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <table
      className={cn("w-full border-collapse text-left text-sm", className)}
      {...props}
    >
      {children}
    </table>
  );
}

export function Th({
  className,
  children,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        "whitespace-nowrap border-b border-line bg-surface-muted px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle first:pl-5 last:pr-5",
        className
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function Td({
  className,
  children,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        "px-4 py-3 align-middle text-sm text-ink first:pl-5 last:pr-5",
        className
      )}
      {...props}
    >
      {children}
    </td>
  );
}

export function Tr({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-line/70 transition-colors last:border-0 hover:bg-surface-hover",
        className
      )}
      {...props}
    >
      {children}
    </tr>
  );
}
