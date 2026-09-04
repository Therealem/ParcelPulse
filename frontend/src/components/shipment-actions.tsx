"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Action = "refresh" | "delete";

type Feedback = {
  status: "success" | "error";
  message: string;
};

async function getApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
    };

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

export function ShipmentActions({
  shipmentId,
  trackingNumber,
}: {
  shipmentId: number;
  trackingNumber: string;
}) {
  const router = useRouter();
  const [activeAction, setActiveAction] = useState<Action | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  async function refreshShipment() {
    setActiveAction("refresh");
    setFeedback(null);

    try {
      const response = await fetch(
        `/api/shipments/${shipmentId}/refresh`,
        {
          method: "POST",
          credentials: "include",
        },
      );

      if (response.status === 401) {
        router.replace(
          `/login?next=${encodeURIComponent(`/shipments/${shipmentId}`)}`,
        );
        return;
      }

      if (!response.ok) {
        throw new Error(
          await getApiError(
            response,
            "We could not refresh this shipment. Please try again.",
          ),
        );
      }

      setFeedback({
        status: "success",
        message: "Shipment refreshed. Tracking history is up to date.",
      });
      router.refresh();
    } catch (error) {
      setFeedback({
        status: "error",
        message:
          error instanceof Error && !(error instanceof TypeError)
            ? error.message
            : "We could not reach the tracking service. Please try again.",
      });
    } finally {
      setActiveAction(null);
    }
  }

  async function deleteShipment() {
    const confirmed = window.confirm(
      `Delete shipment ${trackingNumber}? Its tracking history will also be removed. This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    setActiveAction("delete");
    setFeedback(null);

    try {
      const response = await fetch(
        `/api/shipments/${shipmentId}`,
        { method: "DELETE", credentials: "include" },
      );

      if (response.status === 401) {
        router.replace(
          `/login?next=${encodeURIComponent(`/shipments/${shipmentId}`)}`,
        );
        return;
      }

      if (!response.ok) {
        throw new Error(
          await getApiError(
            response,
            "We could not delete this shipment. Please try again.",
          ),
        );
      }

      router.replace(`/shipments?deleted=${shipmentId}`);
    } catch (error) {
      setFeedback({
        status: "error",
        message:
          error instanceof Error && !(error instanceof TypeError)
            ? error.message
            : "We could not reach the shipment service. Please try again.",
      });
      setActiveAction(null);
    }
  }

  const isBusy = activeAction !== null;

  return (
    <div className="flex flex-col items-start gap-3 lg:items-end">
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isBusy}
          onClick={() => void refreshShipment()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:text-slate-400"
        >
          {activeAction === "refresh" && (
            <span
              aria-hidden="true"
              className="size-3.5 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600"
            />
          )}
          {activeAction === "refresh" ? "Refreshing..." : "Refresh"}
        </button>
        <button
          type="button"
          disabled={isBusy}
          onClick={() => void deleteShipment()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 text-sm font-semibold text-red-700 shadow-sm transition hover:border-red-300 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:cursor-not-allowed disabled:text-red-300"
        >
          {activeAction === "delete" && (
            <span
              aria-hidden="true"
              className="size-3.5 animate-spin rounded-full border-2 border-red-200 border-t-red-600"
            />
          )}
          {activeAction === "delete" ? "Deleting..." : "Delete Shipment"}
        </button>
      </div>

      {feedback && (
        <p
          role={feedback.status === "error" ? "alert" : "status"}
          className={`max-w-sm rounded-lg px-3 py-2 text-sm font-semibold ${
            feedback.status === "success"
              ? "bg-emerald-50 text-emerald-800"
              : "bg-red-50 text-red-700"
          }`}
        >
          {feedback.message}
        </p>
      )}
    </div>
  );
}
