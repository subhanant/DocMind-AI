"use client";

import React, { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { useAuth } from "@/lib/auth-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [user, isLoading, router, pathname]);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    const frame = requestAnimationFrame(() => setSidebarOpen(false));
    return () => cancelAnimationFrame(frame);
  }, [pathname]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-canvas">
        <div className="flex flex-col items-center gap-4">
          <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 via-brand-600 to-cyan-500 text-white shadow-brand">
            <Sparkles className="h-6 w-6 animate-pulse" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-ink">DocMind AI</p>
            <p className="mt-0.5 text-xs text-ink-subtle">Preparing your workspace…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // The wrapper intentionally has no bg-* class: the wash below sits at -z-10 and
  // would otherwise be painted over by the wrapper's own background.
  return (
    <div className="min-h-screen">
      {/* Ambient background wash */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-72 bg-[radial-gradient(60%_100%_at_50%_0%,color-mix(in_oklab,var(--color-brand-500)_14%,transparent),transparent_70%)]"
      />

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-h-screen flex-col lg:pl-64">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
