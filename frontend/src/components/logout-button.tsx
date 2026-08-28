"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export function LogoutButton() {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function logout() {
    if (!apiBaseUrl) {
      return;
    }

    setIsLoggingOut(true);
    try {
      await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      router.replace("/");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={() => void logout()}
      disabled={isLoggingOut}
      className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 px-4 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:text-slate-400"
    >
      {isLoggingOut ? "Signing out..." : "Log out"}
    </button>
  );
}
