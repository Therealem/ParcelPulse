"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

type AuthMode = "login" | "register";

type ApiError = {
  detail?: string | Array<{ msg?: string }>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

async function getApiError(response: Response): Promise<string> {
  const fallback = "We could not complete that request. Please try again.";

  try {
    const body = (await response.json()) as ApiError;
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
  } catch {
    return fallback;
  }

  return fallback;
}

export function AuthForm({
  mode,
  redirectTo = "/shipments",
}: {
  mode: AuthMode;
  redirectTo?: string;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!apiBaseUrl) {
      setError("The authentication service is not configured.");
      return;
    }

    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/auth/${mode}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email, password }),
        },
      );

      if (!response.ok) {
        throw new Error(await getApiError(response));
      }

      router.replace(redirectTo);
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error && !(requestError instanceof TypeError)
          ? requestError.message
          : "We could not reach the authentication service. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-5">
      <label className="block">
        <span className="mb-2 block text-sm font-semibold text-slate-700">
          Email address
        </span>
        <input
          name="email"
          type="email"
          autoComplete="email"
          required
          autoFocus
          className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          placeholder="you@example.com"
        />
      </label>

      <label className="block">
        <span className="mb-2 block text-sm font-semibold text-slate-700">
          Password
        </span>
        <input
          name="password"
          type="password"
          autoComplete={isRegister ? "new-password" : "current-password"}
          minLength={8}
          maxLength={128}
          required
          aria-describedby={isRegister ? "password-help" : undefined}
          className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          placeholder="At least 8 characters"
        />
        {isRegister && (
          <span id="password-help" className="mt-2 block text-xs text-slate-500">
            Use at least 8 characters. A password manager is recommended.
          </span>
        )}
      </label>

      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700"
        >
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-400"
      >
        {isSubmitting && (
          <span
            aria-hidden="true"
            className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
          />
        )}
        {isSubmitting
          ? isRegister
            ? "Creating account..."
            : "Signing in..."
          : isRegister
            ? "Create account"
            : "Sign in"}
      </button>

      <p className="text-center text-sm text-slate-600">
        {isRegister ? "Already have an account?" : "New to ParcelPulse?"}{" "}
        <Link
          href={isRegister ? "/login" : "/register"}
          className="font-semibold text-blue-700 hover:text-blue-800"
        >
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
