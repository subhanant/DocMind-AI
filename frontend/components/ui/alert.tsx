import * as React from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type AlertVariant = "info" | "success" | "warning" | "error";

const VARIANTS: Record<
  AlertVariant,
  { wrapper: string; icon: React.ElementType; iconClass: string }
> = {
  info: {
    wrapper:
      "border-brand-200 bg-brand-50/70 text-brand-800 dark:border-brand-900/60 dark:bg-brand-950/30 dark:text-brand-200",
    icon: Info,
    iconClass: "text-brand-500",
  },
  success: {
    wrapper:
      "border-emerald-200 bg-emerald-50/70 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200",
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
  },
  warning: {
    wrapper:
      "border-amber-200 bg-amber-50/70 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
    icon: AlertTriangle,
    iconClass: "text-amber-500",
  },
  error: {
    wrapper:
      "border-rose-200 bg-rose-50/70 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
    icon: XCircle,
    iconClass: "text-rose-500",
  },
};

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children?: React.ReactNode;
  className?: string;
  /** Optional trailing action (retry button, dismiss, …). */
  action?: React.ReactNode;
  role?: "alert" | "status";
}

export function Alert({
  variant = "info",
  title,
  children,
  className,
  action,
  role = "alert",
}: AlertProps) {
  const { wrapper, icon: Icon, iconClass } = VARIANTS[variant];

  return (
    <div
      role={role}
      className={cn(
        "flex items-start gap-3 rounded-xl border p-3.5 text-sm",
        wrapper,
        className
      )}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", iconClass)} aria-hidden />
      <div className="min-w-0 flex-1">
        {title && <p className="text-sm font-semibold">{title}</p>}
        {children && (
          <div
            className={cn(
              "text-xs leading-relaxed opacity-90",
              title && "mt-0.5"
            )}
          >
            {children}
          </div>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
