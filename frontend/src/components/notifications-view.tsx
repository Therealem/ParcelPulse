"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { notifyUnreadCountChanged } from "@/components/notification-bell";

type Notification = {
  id: number;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

type ViewState =
  | { status: "loading" }
  | { status: "success"; notifications: Notification[] }
  | { status: "error"; message: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function NotificationsView() {
  const router = useRouter();
  const [requestKey, setRequestKey] = useState(0);
  const [view, setView] = useState<ViewState>({ status: "loading" });
  const [activeId, setActiveId] = useState<
    number | "all" | "test" | null
  >(null);
  const [devControlsEnabled, setDevControlsEnabled] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadNotifications() {
      if (!apiBaseUrl) {
        setView({
          status: "error",
          message: "The notification service is not configured.",
        });
        return;
      }

      try {
        const response = await fetch(
          `${apiBaseUrl.replace(/\/$/, "")}/api/notifications`,
          {
            headers: { Accept: "application/json" },
            credentials: "include",
            cache: "no-store",
            signal: controller.signal,
          },
        );
        if (response.status === 401) {
          router.replace("/login?next=%2Fnotifications");
          return;
        }
        if (!response.ok) {
          throw new Error("Notifications could not be loaded.");
        }
        const body = (await response.json()) as unknown;
        if (!Array.isArray(body)) {
          throw new Error("The notification service returned invalid data.");
        }
        setView({
          status: "success",
          notifications: body as Notification[],
        });

        try {
          const devStatusResponse = await fetch(
            `${apiBaseUrl.replace(/\/$/, "")}/api/notifications/dev/status`,
            {
              headers: { Accept: "application/json" },
              credentials: "include",
              cache: "no-store",
              signal: controller.signal,
            },
          );
          if (devStatusResponse.ok) {
            const devStatus = (await devStatusResponse.json()) as {
              enabled?: unknown;
            };
            setDevControlsEnabled(devStatus.enabled === true);
          } else {
            setDevControlsEnabled(false);
          }
        } catch (error) {
          if (!(error instanceof DOMException && error.name === "AbortError")) {
            setDevControlsEnabled(false);
          }
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setView({
          status: "error",
          message:
            "We could not load your notifications. Check that the backend is running, then try again.",
        });
      }
    }

    void loadNotifications();
    return () => controller.abort();
  }, [requestKey, router]);

  async function markOneRead(notificationId: number) {
    if (!apiBaseUrl) {
      return;
    }
    setActiveId(notificationId);
    setActionError(null);
    try {
      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/notifications/${notificationId}/read`,
        { method: "PATCH", credentials: "include" },
      );
      if (response.status === 401) {
        router.replace("/login?next=%2Fnotifications");
        return;
      }
      if (!response.ok) {
        throw new Error("Notification could not be updated.");
      }
      const updated = (await response.json()) as Notification;
      setView((current) =>
        current.status === "success"
          ? {
              status: "success",
              notifications: current.notifications.map((notification) =>
                notification.id === updated.id ? updated : notification,
              ),
            }
          : current,
      );
      notifyUnreadCountChanged();
    } catch {
      setActionError("We could not mark that notification as read.");
    } finally {
      setActiveId(null);
    }
  }

  async function markAllRead() {
    if (!apiBaseUrl) {
      return;
    }
    setActiveId("all");
    setActionError(null);
    try {
      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/notifications/read-all`,
        { method: "PATCH", credentials: "include" },
      );
      if (response.status === 401) {
        router.replace("/login?next=%2Fnotifications");
        return;
      }
      if (!response.ok) {
        throw new Error("Notifications could not be updated.");
      }
      setView((current) =>
        current.status === "success"
          ? {
              status: "success",
              notifications: current.notifications.map((notification) => ({
                ...notification,
                is_read: true,
              })),
            }
          : current,
      );
      notifyUnreadCountChanged();
    } catch {
      setActionError("We could not mark all notifications as read.");
    } finally {
      setActiveId(null);
    }
  }

  async function createTestNotification() {
    if (!apiBaseUrl) {
      return;
    }
    setActiveId("test");
    setActionError(null);
    try {
      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/notifications/dev/test`,
        { method: "POST", credentials: "include" },
      );
      if (response.status === 401) {
        router.replace("/login?next=%2Fnotifications");
        return;
      }
      if (response.status === 404) {
        setDevControlsEnabled(false);
        throw new Error("Development notifications are not enabled.");
      }
      if (!response.ok) {
        throw new Error("Test notification could not be created.");
      }
      const created = (await response.json()) as Notification;
      setView((current) =>
        current.status === "success"
          ? {
              status: "success",
              notifications: [created, ...current.notifications],
            }
          : current,
      );
      notifyUnreadCountChanged();
      setRequestKey((key) => key + 1);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "We could not create the development test notification.",
      );
    } finally {
      setActiveId(null);
    }
  }

  if (view.status === "loading") {
    return (
      <div className="mt-10 space-y-4" aria-label="Loading notifications">
        {[0, 1, 2].map((item) => (
          <div
            key={item}
            className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white/80"
          />
        ))}
      </div>
    );
  }

  if (view.status === "error") {
    return (
      <div className="mt-10 rounded-2xl border border-red-100 bg-white p-7 text-center shadow-sm">
        <h2 className="text-xl font-bold text-slate-950">
          Notifications unavailable
        </h2>
        <p className="mx-auto mt-2 max-w-lg leading-7 text-slate-600">
          {view.message}
        </p>
        <button
          type="button"
          onClick={() => {
            setView({ status: "loading" });
            setRequestKey((key) => key + 1);
          }}
          className="mt-5 inline-flex h-10 items-center rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white transition hover:bg-blue-700"
        >
          Try again
        </button>
      </div>
    );
  }

  const unreadCount = view.notifications.filter(
    (notification) => !notification.is_read,
  ).length;

  return (
    <section className="mt-10" aria-labelledby="notification-list-heading">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2
            id="notification-list-heading"
            className="text-lg font-bold text-slate-950"
          >
            Recent updates
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount === 1 ? "" : "s"}`
              : "You are all caught up."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {devControlsEnabled && (
            <button
              type="button"
              disabled={activeId !== null}
              onClick={() => void createTestNotification()}
              className="inline-flex h-10 w-fit items-center rounded-xl border border-amber-300 bg-amber-50 px-4 text-sm font-semibold text-amber-800 shadow-sm transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {activeId === "test"
                ? "Creating test..."
                : "Create test notification"}
            </button>
          )}
          {unreadCount > 0 && (
            <button
              type="button"
              disabled={activeId !== null}
              onClick={() => void markAllRead()}
              className="inline-flex h-10 w-fit items-center rounded-xl border border-blue-200 bg-white px-4 text-sm font-semibold text-blue-700 shadow-sm transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {activeId === "all" ? "Updating..." : "Mark all as read"}
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <p
          role="alert"
          className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700"
        >
          {actionError}
        </p>
      )}

      {view.notifications.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white/70 px-6 py-14 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-full bg-blue-50 text-blue-600">
            <span aria-hidden="true" className="text-xl">
              &#10003;
            </span>
          </span>
          <h3 className="mt-4 text-lg font-bold text-slate-950">
            No notifications yet
          </h3>
          <p className="mx-auto mt-2 max-w-md leading-7 text-slate-500">
            Important delivery changes, such as out for delivery or delivered,
            will appear here.
          </p>
        </div>
      ) : (
        <ol className="mt-6 space-y-4">
          {view.notifications.map((notification) => (
            <li
              key={notification.id}
              className={`rounded-2xl border bg-white px-5 py-5 shadow-[0_12px_32px_rgba(15,23,42,0.05)] sm:px-6 ${
                notification.is_read
                  ? "border-slate-200"
                  : "border-blue-200 ring-1 ring-blue-100"
              }`}
            >
              <div className="flex gap-4">
                <span
                  aria-hidden="true"
                  className={`mt-2 size-2.5 shrink-0 rounded-full ${
                    notification.is_read ? "bg-slate-300" : "bg-blue-600"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="font-bold text-slate-950">
                        {notification.title}
                      </h3>
                      <p className="mt-1 leading-7 text-slate-600">
                        {notification.message}
                      </p>
                    </div>
                    <time
                      dateTime={notification.created_at}
                      className="shrink-0 text-xs font-semibold uppercase tracking-[0.08em] text-slate-400"
                    >
                      {formatTimestamp(notification.created_at)}
                    </time>
                  </div>
                  {!notification.is_read && (
                    <button
                      type="button"
                      disabled={activeId !== null}
                      onClick={() => void markOneRead(notification.id)}
                      className="mt-4 text-sm font-semibold text-blue-700 transition hover:text-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {activeId === notification.id
                        ? "Updating..."
                        : "Mark as read"}
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
