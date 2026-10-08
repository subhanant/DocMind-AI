import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border font-medium transition-colors whitespace-nowrap [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/50 dark:text-brand-300",
        neutral:
          "border-line bg-surface-muted text-ink-muted dark:border-line dark:bg-surface-muted",
        destructive:
          "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/50 dark:text-rose-300",
        success:
          "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/50 dark:text-emerald-300",
        warning:
          "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-300",
        info: "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900/60 dark:bg-cyan-950/50 dark:text-cyan-300",
        outline: "border-line-strong bg-transparent text-ink-muted",
      },
      size: {
        sm: "px-2 py-0.5 text-[10px] [&_svg]:size-3",
        md: "px-2.5 py-0.5 text-xs [&_svg]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
