"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
const notificationsChangedEvent = "parcelpulse:notifications-changed";

export function notifyUnreadCountChanged() {
  window.dispatchEvent(new Event(notificationsChangedEvent));
}

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState<number | null>(null);

  useEffect(() => {
    if (!apiBaseUrl) {
      return;
    }

    let active = true;

    async function loadUnreadCount() {
      try {
        const response = await fetch(
          `${apiBaseUrl?.replace(/\/$/, "")}/api/notifications/unread-count`,
          {
            headers: { Accept: "application/json" },
            credentials: "include",
            cache: "no-store",
          },
        );
        if (!response.ok) {
          return;
        }
        const body = (await response.json()) as { unread_count?: unknown };
        if (
          active &&
          typeof body.unread_count === "number" &&
          Number.isInteger(body.unread_count) &&
          body.unread_count >= 0
        ) {
          setUnreadCount(body.unread_count);
        }
      } catch {
        // The navigation remains usable when the optional badge cannot load.
      }
    }

    const refresh = () => void loadUnreadCount();
    void loadUnreadCount();
    const interval = window.setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);
    window.addEventListener(notificationsChangedEvent, refresh);

    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", refresh);
      window.removeEventListener(notificationsChangedEvent, refresh);
    };
  }, []);

  const label =
    unreadCount && unreadCount > 0
      ? `Notifications, ${unreadCount} unread`
      : "Notifications";

  return (
    <Link
      href="/notifications"
      aria-label={label}
      title="Notifications"
      className="relative inline-grid size-10 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white/80 text-slate-600 shadow-sm backdrop-blur transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        className="size-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </svg>
      {unreadCount !== null && unreadCount > 0 && (
        <span className="absolute -right-1.5 -top-1.5 grid min-h-5 min-w-5 place-items-center rounded-full bg-blue-600 px-1 text-[0.65rem] font-bold leading-none text-white ring-2 ring-white">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </Link>
  );
}
