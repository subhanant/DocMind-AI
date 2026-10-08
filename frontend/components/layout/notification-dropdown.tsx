"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bell, CheckCheck, FileCheck2, Info } from "lucide-react";
import { NotificationItem } from "@/types";
import { api } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

const TYPE_STYLES: Record<string, { plate: string; icon: React.ElementType }> = {
  upload_complete: {
    plate: "bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300",
    icon: FileCheck2,
  },
  processing_complete: {
    plate:
      "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300",
    icon: FileCheck2,
  },
  processing_failed: {
    plate: "bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-300",
    icon: AlertTriangle,
  },
  needs_review: {
    plate: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300",
    icon: AlertTriangle,
  },
};

export function NotificationDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = React.useCallback(async () => {
    try {
      const res = await api.notifications.list({ page: 1, size: 6 });
      setNotifications(res.items);
      setUnreadCount(res.items.filter((n) => !n.is_read).length);
    } catch {
      // Silently ignore — the user may simply not be authenticated yet.
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => void fetchNotifications(), 0);
    const interval = setInterval(() => void fetchNotifications(), 30_000);
    return () => {
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, [fetchNotifications]);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await api.notifications.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // no-op: the UI keeps its previous state
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.notifications.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // no-op
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={
          unreadCount > 0
            ? `Notifications, ${unreadCount} unread`
            : "Notifications"
        }
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className={cn(
          "focus-ring relative rounded-lg p-2 transition-colors",
          isOpen
            ? "bg-surface-hover text-ink"
            : "text-ink-muted hover:bg-surface-hover hover:text-ink"
        )}
      >
        <Bell className="h-[18px] w-[18px]" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white ring-2 ring-surface">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 z-50 mt-2 w-[min(24rem,calc(100vw-2rem))] animate-scale-in overflow-hidden rounded-2xl border border-line bg-surface shadow-pop"
        >
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-ink">Notifications</h2>
              {unreadCount > 0 && (
                <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[11px] font-semibold text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="focus-ring inline-flex items-center gap-1 rounded-md text-xs font-medium text-brand-600 transition-colors hover:text-brand-700 dark:text-brand-300"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[min(22rem,60vh)] divide-y divide-line overflow-y-auto">
            {isLoading ? (
              <div className="space-y-3 p-4">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="flex gap-3">
                    <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-3 w-2/3" />
                      <Skeleton className="h-2.5 w-full" />
                    </div>
                  </div>
                ))}
              </div>
            ) : notifications.length === 0 ? (
              <EmptyState
                compact
                icon={Bell}
                title="No notifications yet"
                description="Upload a document to receive processing alerts here."
              />
            ) : (
              notifications.map((item) => {
                const style = TYPE_STYLES[item.type] ?? {
                  plate: "bg-surface-muted text-ink-subtle",
                  icon: Info,
                };
                const Icon = style.icon;
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "relative flex gap-3 p-3.5 transition-colors hover:bg-surface-hover",
                      !item.is_read && "bg-brand-50/40 dark:bg-brand-950/15"
                    )}
                  >
                    {!item.is_read && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-0 h-full w-0.5 bg-brand-500"
                      />
                    )}
                    <span
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg [&_svg]:size-4",
                        style.plate
                      )}
                    >
                      <Icon />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p
                          className={cn(
                            "text-xs leading-snug",
                            item.is_read
                              ? "font-medium text-ink-muted"
                              : "font-semibold text-ink"
                          )}
                        >
                          {item.title}
                        </p>
                        <span className="shrink-0 text-[10px] tabular text-ink-subtle">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                      <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-ink-muted">
                        {item.message}
                      </p>
                      <div className="mt-2 flex items-center gap-3">
                        {item.document_id && (
                          <Link
                            href={`/documents/${item.document_id}`}
                            onClick={() => setIsOpen(false)}
                            className="focus-ring rounded text-[11px] font-semibold text-brand-600 hover:underline dark:text-brand-300"
                          >
                            View document
                          </Link>
                        )}
                        {!item.is_read && (
                          <button
                            type="button"
                            onClick={() => handleMarkAsRead(item.id)}
                            className="focus-ring rounded text-[11px] text-ink-subtle transition-colors hover:text-ink"
                          >
                            Mark read
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <Link
            href="/notifications"
            onClick={() => setIsOpen(false)}
            className="focus-ring block border-t border-line bg-surface-muted py-2.5 text-center text-xs font-semibold text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
          >
            View all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
