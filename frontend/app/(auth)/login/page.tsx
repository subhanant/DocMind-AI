"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowRight, Eye, EyeOff, Loader2, Mail, Lock } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input, Field } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { AuthShell } from "@/components/auth/auth-shell";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email || !password) {
      setError("Please enter both your email and password.");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      await login(email, password);
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Invalid email or password. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your DocMind AI workspace to keep processing documents."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="focus-ring rounded font-semibold text-brand-600 hover:underline dark:text-brand-300"
          >
            Create one now
          </Link>
        </>
      }
    >
      {error && (
        <Alert variant="error" title="Sign-in failed" className="mb-5">
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <Field id="email" label="Email address" required>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@company.com"
            autoComplete="email"
            leadingIcon={<Mail />}
            invalid={Boolean(error) && !email}
          />
        </Field>

        <Field id="password" label="Password" required>
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            leadingIcon={<Lock />}
            invalid={Boolean(error) && !password}
            trailingSlot={
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="focus-ring rounded-md p-1.5 text-ink-subtle transition-colors hover:text-ink"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            }
          />
        </Field>

        <Button type="submit" disabled={isLoading} className="w-full gap-2">
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Signing in…
            </>
          ) : (
            <>
              Sign in
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      <p className="mt-6 border-t border-line pt-5 text-center text-[11px] leading-relaxed text-ink-subtle">
        Running locally? Register an account with a password of at least 8 characters,
        including one uppercase letter and one number.
      </p>
    </AuthShell>
  );
}
