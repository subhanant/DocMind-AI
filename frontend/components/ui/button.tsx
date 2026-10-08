import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "focus-ring relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-[var(--ease-settle)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50 cursor-pointer [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-brand-600 text-white shadow-soft hover:bg-brand-700 hover:shadow-brand active:bg-brand-800",
        destructive:
          "bg-rose-600 text-white shadow-soft hover:bg-rose-700 active:bg-rose-800",
        outline:
          "border border-line bg-surface text-ink shadow-card hover:border-line-strong hover:bg-surface-hover",
        secondary:
          "bg-surface-muted text-ink shadow-card hover:bg-surface-hover",
        ghost: "text-ink-muted hover:bg-surface-hover hover:text-ink",
        link: "h-auto p-0 text-brand-600 underline-offset-4 hover:underline dark:text-brand-300",
      },
      size: {
        default: "h-9 px-4 [&_svg]:size-4",
        sm: "h-8 gap-1.5 rounded-lg px-3 text-xs [&_svg]:size-3.5",
        lg: "h-11 rounded-xl px-6 text-sm [&_svg]:size-4",
        icon: "h-9 w-9 p-0 [&_svg]:size-4",
        "icon-sm": "h-8 w-8 rounded-lg p-0 [&_svg]:size-4",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
