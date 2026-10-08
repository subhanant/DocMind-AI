"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  Settings,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { cn, getInitials } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type NavItem = { name: string; href: string; icon: React.ElementType };

const NAV_SECTIONS: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Workspace",
    items: [
      { name: "Dashboard", href: "/", icon: LayoutDashboard },
      { name: "Documents", href: "/documents", icon: FileText },
      { name: "Upload", href: "/upload", icon: UploadCloud },
    ],
  },
  {
    label: "Automations",
    items: [
      { name: "Email Connections", href: "/email-connections", icon: Mail },
      { name: "Notifications", href: "/notifications", icon: Bell },
    ],
  },
  {
    label: "Account",
    items: [{ name: "Settings", href: "/settings", icon: Settings }],
  },
];

export function Sidebar({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <>
      {/* Mobile backdrop */}
      <div
        onClick={onClose}
        aria-hidden
        className={cn(
          "fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm transition-opacity duration-200 lg:hidden",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />

      <aside
        aria-label="Main navigation"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-surface transition-transform duration-300 ease-out lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-500 via-brand-600 to-cyan-500 text-white shadow-brand">
            <Sparkles className="h-5 w-5" />
            <span className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/25" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-1">
              <span className="truncate text-[15px] font-bold tracking-tight text-ink">
                DocMind
              </span>
              <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
                AI
              </span>
            </div>
            <p className="truncate text-[11px] font-medium text-ink-subtle">
              Document Intelligence
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="focus-ring rounded-lg p-1.5 text-ink-subtle transition-colors hover:bg-surface-hover hover:text-ink lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="space-y-1">
              <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-subtle">
                {section.label}
              </p>
              {section.items.map((item) => {
                const active = isActive(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={onClose}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "focus-ring group relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150",
                      active
                        ? "bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-200"
                        : "text-ink-muted hover:bg-surface-hover hover:text-ink"
                    )}
                  >
                    {active && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-brand-600 dark:bg-brand-400"
                      />
                    )}
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        active
                          ? "text-brand-600 dark:text-brand-300"
                          : "text-ink-subtle group-hover:text-ink-muted"
                      )}
                    />
                    <span className="truncate">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Pipeline status */}
        <div className="mx-3 mb-3 rounded-xl border border-line bg-surface-muted p-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ring rounded-full bg-emerald-400" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <p className="text-[11px] font-semibold text-ink">Extraction pipeline</p>
            <span className="ml-auto rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
              Live
            </span>
          </div>
          <p className="mt-1.5 text-[11px] leading-snug text-ink-subtle">
            OCR, classification and schema extraction are running.
          </p>
        </div>

        {/* Account footer */}
        <div className="border-t border-line p-3">
          <div className="flex items-center gap-2.5 rounded-xl bg-surface-muted p-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-xs font-bold text-white shadow-soft">
              {getInitials(user?.full_name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-ink">
                {user?.full_name || "User"}
              </p>
              <p className="truncate text-[11px] text-ink-subtle">{user?.email}</p>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => logout()}
              title="Sign out"
              aria-label="Sign out"
              className="shrink-0 text-ink-subtle hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>
    </>
  );
}
