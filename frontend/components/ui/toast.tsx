"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastVariant = "success" | "error" | "info" | "warning";

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  /** Auto-dismiss delay in ms. Pass 0 to keep it until dismissed. */
  duration?: number;
}

interface ToastRecord extends ToastOptions {
  id: number;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (options: ToastOptions) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const VARIANT_STYLES: Record<
  ToastVariant,
  { icon: React.ElementType; iconClass: string; accent: string }
> = {
  success: {
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    accent: "bg-emerald-500",
  },
  error: {
    icon: XCircle,
    iconClass: "text-rose-500",
    accent: "bg-rose-500",
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    accent: "bg-amber-500",
  },
  info: {
    icon: Info,
    iconClass: "text-brand-500",
    accent: "bg-brand-500",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const toast = useCallback(
    (options: ToastOptions) => {
      const id = nextId.current++;
      const record: ToastRecord = { variant: "info", duration: 4500, ...options, id };
      setToasts((prev) => [...prev.slice(-3), record]);
      if (record.duration && record.duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), record.duration)
        );
      }
    },
    [dismiss]
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  const value: ToastContextValue = {
    toast,
    success: (title, description) => toast({ title, description, variant: "success" }),
    error: (title, description) => toast({ title, description, variant: "error", duration: 6500 }),
    info: (title, description) => toast({ title, description, variant: "info" }),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-3 bottom-3 z-[100] flex flex-col items-stretch gap-2 sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-96"
      >
        {toasts.map((item) => {
          const { icon: Icon, iconClass, accent } = VARIANT_STYLES[item.variant];
          return (
            <div
              key={item.id}
              role="status"
              className="pointer-events-auto relative flex animate-fade-up items-start gap-3 overflow-hidden rounded-xl border border-line bg-surface p-3.5 pl-4 shadow-pop"
            >
              <span className={cn("absolute inset-y-0 left-0 w-1", accent)} aria-hidden />
              <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", iconClass)} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{item.title}</p>
                {item.description && (
                  <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                    {item.description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismiss(item.id)}
                aria-label="Dismiss notification"
                className="focus-ring -m-1 rounded-md p-1 text-ink-subtle transition-colors hover:bg-surface-hover hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
