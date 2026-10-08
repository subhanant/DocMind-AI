"use client";

import React, { useState, useEffect } from "react";
import { User, Shield, Server, Activity, CheckCircle2, RefreshCw } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { user } = useAuth();
  const [healthStatus, setHealthStatus] = useState<{
    status: string;
    environment: string;
    version: string;
  } | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  const checkHealth = async () => {
    try {
      setIsCheckingHealth(true);
      const res = await api.health.check();
      setHealthStatus(res);
    } catch {
      setHealthStatus(null);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Settings & System
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Manage your account profile and verify backend processing node connectivity.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User Profile Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-lg bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <User className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold">User Profile</CardTitle>
                <CardDescription className="text-xs">
                  Your local authentication profile
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Full Name</span>
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                {user?.full_name || "—"}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Email</span>
              <span className="font-mono text-slate-700 dark:text-slate-300">
                {user?.email || "—"}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Role</span>
              <span className="capitalize px-2 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 text-[11px] font-semibold">
                {user?.role || "user"}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">User ID</span>
              <span className="font-mono text-[10px] text-slate-400 truncate max-w-[200px]">
                {user?.id || "—"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Backend API Health Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-lg bg-emerald-50 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">
                    FastAPI Health Status
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Connection to backend processing node
                  </CardDescription>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={checkHealth}
                disabled={isCheckingHealth}
                className="h-8 w-8 p-0"
                title="Refresh health check"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${
                    isCheckingHealth ? "animate-spin" : ""
                  }`}
                />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">API Status</span>
              {healthStatus?.status === "healthy" ? (
                <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
                </span>
              ) : (
                <span className="text-rose-500 font-semibold">
                  Checking / Offline
                </span>
              )}
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Environment</span>
              <span className="font-mono text-slate-700 dark:text-slate-300">
                {healthStatus?.environment || "development"}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">API Version</span>
              <span className="font-mono text-slate-700 dark:text-slate-300">
                {healthStatus?.version || "1.0.0"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Architecture Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-sm font-semibold">
              Security Compliance & Architectural Guardrails
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-1">
            <h5 className="font-semibold text-slate-900 dark:text-white">
              Password Hashing
            </h5>
            <p className="text-slate-500 dark:text-slate-400">
              Argon2id with 64MB memory, 3 iterations, and 4 threads. Constant-time dummy verification prevents timing attacks.
            </p>
          </div>

          <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-1">
            <h5 className="font-semibold text-slate-900 dark:text-white">
              Secure Storage Abstraction
            </h5>
            <p className="text-slate-500 dark:text-slate-400">
              Sanitized UUID filenames, MIME magic verification, path traversal prevention, and pluggable cloud S3 interface.
            </p>
          </div>

          <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-1">
            <h5 className="font-semibold text-slate-900 dark:text-white">
              Bill of Lading Schema
            </h5>
            <p className="text-slate-500 dark:text-slate-400">
              Nullable typed fields for shipment, cargo, containers, freight, and dangerous goods with confidence scores.
            </p>
          </div>

          <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-1">
            <h5 className="font-semibold text-slate-900 dark:text-white">
              Encrypted Token Vault
            </h5>
            <p className="text-slate-500 dark:text-slate-400">
              Pre-provisioned EmailConnection database entities require encryption keys prior to OAuth token storage.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
