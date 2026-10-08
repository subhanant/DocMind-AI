"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bell,
  CheckCheck,
  ExternalLink,
  FileCheck2,
  Info,
} from "lucide-react";
import { NotificationItem } from "@/types";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import { motionVars } from "@/components/motion/reveal";

const PAGE_SIZE = 15;

const TYPE_STYLES: Record<string, { plate: string; icon: React.ElementType }> = {
  upload_complete: {
    plate: "bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300",
    icon: FileCheck2,
  },
  processing_complete: {
    plate: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300",
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

const FILTERS = [
  { value: false, label: "All notifications" },
  { value: true, label: "Unread only" },
];

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.notifications.list({
        page,
        size: PAGE_SIZE,
        unread_only: unreadOnly,
      });
      setNotifications(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch {
      // Fail quietly — the empty state covers this case.
    } finally {
      setIsLoading(false);
    }
  }, [page, unreadOnly]);

  useEffect(() => {
    const timeout = setTimeout(() => void loadNotifications(), 0);
    return () => clearTimeout(timeout);
  }, [loadNotifications]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await api.notifications.markAsRead(id);
      setNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
    } catch {
      // no-op
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.notifications.markAllAsRead();
      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
    } catch {
      // no-op
    }
  };

  const unreadCount = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Activity"
        title="Notifications"
        description="Upload confirmations, extraction results and processing alerts for your workspace."
        actions={
          <Button variant="outline" size="sm" onClick={handleMarkAllRead} className="gap-1.5">
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all as read
          </Button>
        }
      />

      {/* Filter segmented control */}
      <div
        role="tablist"
        aria-label="Notification filter"
        className="inline-flex items-center gap-1 rounded-xl border border-line bg-surface-muted p-1"
      >
        {FILTERS.map((filter) => {
          const active = unreadOnly === filter.value;
          return (
            <button
              key={filter.label}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => {
                setUnreadOnly(filter.value);
                setPage(1);
              }}
              className={cn(
                "focus-ring rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors duration-200 ease-[var(--ease-settle)]",
                active
                  ? "bg-surface text-ink shadow-card"
                  : "text-ink-muted hover:bg-surface-hover hover:text-ink"
              )}
            >
              {filter.label}
              {filter.value && unreadCount > 0 && (
                <span className="ml-1.5 rounded-full bg-brand-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <Card
        className="overflow-hidden motion-settle"
        style={motionVars({ index: 1 })}
      >
        {isLoading ? (
          <div className="divide-y divide-line">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="flex gap-4 p-5">
                <Skeleton className="h-10 w-10 shrink-0 rounded-xl" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-1/3" />
                  <Skeleton className="h-2.5 w-3/4" />
                </div>
              </div>
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={Bell}
            title={unreadOnly ? "You're all caught up" : "No notifications yet"}
            description={
              unreadOnly
                ? "There are no unread notifications in your workspace."
                : "Upload a document and status updates will appear here automatically."
            }
            action={
              !unreadOnly ? (
                <Link href="/upload">
                  <Button size="sm">Upload a document</Button>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <ul className="divide-y divide-line">
            {notifications.map((item, index) => {
              const style = TYPE_STYLES[item.type] ?? {
                plate: "bg-surface-muted text-ink-subtle",
                icon: Info,
              };
              const Icon = style.icon;

              return (
                <li
                  key={item.id}
                  className={cn(
                    "relative flex items-start gap-4 p-5 transition-colors duration-200 motion-fade",
                    item.is_read ? "hover:bg-surface-hover" : "bg-brand-50/30 dark:bg-brand-950/15"
                  )}
                  style={motionVars({ index: Math.min(index, 8), duration: "0.4s" })}
                >
                  {!item.is_read && (
                    <span
                      aria-hidden
                      className="absolute left-0 top-0 h-full w-0.5 bg-brand-500"
                    />
                  )}

                  <span
                    className={cn(
                      "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl [&_svg]:size-5",
                      style.plate
                    )}
                  >
                    <Icon />
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <h3
                        className={cn(
                          "text-sm",
                          item.is_read
                            ? "font-medium text-ink-muted"
                            : "font-semibold text-ink"
                        )}
                      >
                        {item.title}
                      </h3>
                      <time
                        dateTime={item.created_at}
                        title={formatDateTime(item.created_at)}
                        className="shrink-0 text-[11px] text-ink-subtle"
                      >
                        {formatDate(item.created_at)}
                      </time>
                    </div>

                    <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                      {item.message}
                    </p>

                    <div className="mt-3 flex flex-wrap items-center gap-4">
                      {item.document_id && (
                        <Link
                          href={`/documents/${item.document_id}`}
                          className="focus-ring inline-flex items-center gap-1 rounded text-xs font-semibold text-brand-600 hover:underline dark:text-brand-300"
                        >
                          Inspect document
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      )}
                      {!item.is_read && (
                        <button
                          type="button"
                          onClick={() => handleMarkAsRead(item.id)}
                          className="focus-ring rounded text-xs text-ink-subtle transition-colors hover:text-ink"
                        >
                          Mark as read
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {totalPages > 1 && (
          <Pagination
            page={page}
            totalPages={totalPages}
            total={total}
            pageSize={PAGE_SIZE}
            isLoading={isLoading}
            onPageChange={setPage}
            label="notifications"
          />
        )}
      </Card>
    </div>
  );
}
