"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Menu, Moon, Search, Sparkles, Sun, UploadCloud, X } from "lucide-react";
import { NotificationDropdown } from "./notification-dropdown";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { cn, getInitials } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const router = useRouter();
  const { user } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearchSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const query = searchTerm.trim();
    router.push(query ? `/documents?search=${encodeURIComponent(query)}` : "/documents");
  };

  // ⌘K / Ctrl+K focuses the global document search.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center gap-3 border-b border-line bg-surface/85 px-4 backdrop-blur-xl sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation"
        className="focus-ring rounded-lg p-2 text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Global search */}
      <form onSubmit={handleSearchSubmit} className="relative min-w-0 flex-1 sm:max-w-md">
        <Search
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
        />
        <input
          ref={inputRef}
          type="search"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search documents…"
          aria-label="Search documents"
          className="focus-ring h-9 w-full rounded-xl border border-line bg-surface-muted pl-9 pr-16 text-sm text-ink transition-[background-color,border-color] duration-150 placeholder:text-ink-subtle hover:border-line-strong focus:bg-surface [&::-webkit-search-cancel-button]:hidden"
        />
        {searchTerm ? (
          <button
            type="button"
            onClick={() => {
              setSearchTerm("");
              inputRef.current?.focus();
            }}
            aria-label="Clear search"
            className="focus-ring absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-subtle transition-colors hover:bg-surface-hover hover:text-ink"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : (
          <kbd
            aria-hidden
            className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line bg-surface px-1.5 py-0.5 text-[10px] font-medium text-ink-subtle sm:block"
          >
            ⌘K
          </kbd>
        )}
      </form>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
        <Link href="/upload" className="hidden sm:block">
          <Button size="sm" className="gap-1.5">
            <UploadCloud className="h-4 w-4" />
            Upload
          </Button>
        </Link>

        <button
          type="button"
          onClick={toggleTheme}
          aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
          title={isDark ? "Switch to light theme" : "Switch to dark theme"}
          className="focus-ring rounded-lg p-2 text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
        >
          {isDark ? (
            <Sun className="h-[18px] w-[18px] text-amber-400" />
          ) : (
            <Moon className="h-[18px] w-[18px]" />
          )}
        </button>

        <NotificationDropdown />

        <div className="mx-1 hidden h-6 w-px bg-line sm:block" />

        <Link
          href="/settings"
          className={cn(
            "focus-ring group flex items-center gap-2.5 rounded-xl p-1 pr-2 transition-colors hover:bg-surface-hover"
          )}
          aria-label="Account settings"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-[11px] font-bold text-white shadow-soft">
            {getInitials(user?.full_name)}
          </span>
          <span className="hidden text-xs font-semibold text-ink group-hover:text-brand-600 dark:group-hover:text-brand-300 lg:block">
            {user?.full_name?.split(" ")[0] || "Account"}
          </span>
        </Link>
      </div>

      {/* Mobile upload shortcut */}
      <Link href="/upload" className="sm:hidden" aria-label="Upload document">
        <span className="focus-ring flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
          <Sparkles className="h-4 w-4" />
        </span>
      </Link>
    </header>
  );
}
