"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Database,
  KeyRound,
  RefreshCw,
  Server,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDateTime, getInitials } from "@/lib/utils";

interface HealthStatus {
  status: string;
  environment: string;
  version: string;
}

const SECURITY_CARDS = [
  {
    icon: KeyRound,
    title: "Password hashing",
    body: "Argon2id with 64 MB memory, 3 iterations and 4 threads, plus constant-time dummy verification to prevent timing attacks.",
  },
  {
    icon: Database,
    title: "Secure storage abstraction",
    body: "Sanitised UUID filenames, MIME magic verification, path-traversal prevention and a pluggable S3-compatible interface.",
  },
  {
    icon: Server,
    title: "Typed extraction schema",
    body: "Nullable typed fields for shipment, cargo, containers, freight and dangerous goods, each with a confidence score.",
  },
  {
    icon: ShieldCheck,
    title: "Encrypted token vault",
    body: "Email connection records are provisioned for encrypted OAuth token storage, so plaintext secrets are never persisted.",
  },
];

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line py-2.5 last:border-0">
      <dt className="text-xs font-medium text-ink-muted">{label}</dt>
      <dd className="min-w-0 truncate text-right text-xs font-semibold text-ink">
        {children}
      </dd>
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);

  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      setHealthStatus(await api.health.check());
    } catch {
      setHealthStatus(null);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => void checkHealth(), 0);
    return () => clearTimeout(timeout);
  }, [checkHealth]);

  const isHealthy = healthStatus?.status === "healthy";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Account"
        title="Settings & system"
        description="Your profile details and the live status of the DocMind AI processing service."
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Profile */}
        <Card className="overflow-hidden">
          <div className="flex items-center gap-3 border-b border-line px-5 py-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300 [&_svg]:size-4">
              <UserIcon />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-ink">User profile</h2>
              <p className="text-xs text-ink-subtle">Your authenticated account</p>
            </div>
          </div>

          <div className="flex items-center gap-4 border-b border-line px-5 py-5">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-base font-bold text-white shadow-soft">
              {getInitials(user?.full_name)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">
                {user?.full_name || "—"}
              </p>
              <p className="truncate text-xs text-ink-muted">{user?.email || "—"}</p>
            </div>
          </div>

          <dl className="px-5 py-3">
            <Row label="Full name">{user?.full_name || "—"}</Row>
            <Row label="Email">
              <span className="font-mono text-[11px]">{user?.email || "—"}</span>
            </Row>
            <Row label="Role">
              <Badge variant="default" size="sm" className="capitalize">
                {user?.role || "user"}
              </Badge>
            </Row>
            <Row label="Member since">
              {user?.created_at ? formatDateTime(user.created_at) : "—"}
            </Row>
            <Row label="User ID">
              <span className="font-mono text-[10px] text-ink-subtle">{user?.id || "—"}</span>
            </Row>
          </dl>
        </Card>

        {/* Backend health */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-xl [&_svg]:size-4",
                  isHealthy
                    ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300"
                    : "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300"
                )}
              >
                <Activity />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-ink">Processing service</h2>
                <p className="text-xs text-ink-subtle">Backend connectivity</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => checkHealth()}
              disabled={isCheckingHealth}
              aria-label="Refresh health check"
              title="Refresh health check"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isCheckingHealth && "animate-spin")} />
            </Button>
          </div>

          <div className="px-5 py-5">
            <div className="flex items-center gap-3 rounded-xl border border-line bg-surface-muted/60 p-4">
              <span className="relative flex h-2.5 w-2.5 shrink-0">
                {isHealthy && (
                  <span className="absolute inline-flex h-full w-full animate-ring rounded-full bg-emerald-400" />
                )}
                <span
                  className={cn(
                    "relative inline-flex h-2.5 w-2.5 rounded-full",
                    isHealthy ? "bg-emerald-500" : "bg-amber-500"
                  )}
                />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">
                  {isCheckingHealth ? "Checking…" : isHealthy ? "Operational" : "Unreachable"}
                </p>
                <p className="text-xs text-ink-muted">
                  {isHealthy
                    ? "The extraction API is responding normally."
                    : "Start the backend service to enable document processing."}
                </p>
              </div>
            </div>

            <dl className="mt-3">
              {isCheckingHealth && !healthStatus ? (
                <div className="space-y-3 py-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              ) : (
                <>
                  <Row label="API status">
                    <span className={isHealthy ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}>
                      {healthStatus?.status ?? "offline"}
                    </span>
                  </Row>
                  <Row label="Environment">
                    <span className="font-mono text-[11px]">
                      {healthStatus?.environment ?? "development"}
                    </span>
                  </Row>
                  <Row label="API version">
                    <span className="font-mono text-[11px]">
                      {healthStatus?.version ?? "1.0.0"}
                    </span>
                  </Row>
                </>
              )}
            </dl>
          </div>
        </Card>
      </div>

      {/* Security architecture */}
      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 border-b border-line px-5 py-4">
          <ShieldCheck className="h-4 w-4 text-brand-500" aria-hidden />
          <h2 className="text-sm font-semibold text-ink">
            Security & architectural guardrails
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2">
          {SECURITY_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-xl border border-line bg-surface-muted/50 p-4 transition-colors hover:bg-surface-hover"
            >
              <card.icon className="h-4 w-4 text-brand-500" aria-hidden />
              <h3 className="mt-2.5 text-xs font-semibold text-ink">{card.title}</h3>
              <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">{card.body}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
