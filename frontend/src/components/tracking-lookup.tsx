"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

type Shipment = {
  tracking_number: string;
  carrier: string;
  status: string;
  estimated_delivery: string;
  latest_update: string;
};

type ApiError = {
  detail?: string | Array<{ msg?: string }>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

async function getApiError(response: Response): Promise<string> {
  const fallback = "We could not look up that package. Please try again.";

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

export function TrackingLookup() {
  const [trackingNumber, setTrackingNumber] = useState("");
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedTrackingNumber = trackingNumber.replace(/\s/g, "");

    if (!normalizedTrackingNumber) {
      setShipment(null);
      setError("Enter a tracking number to continue.");
      return;
    }

    if (!apiBaseUrl) {
      setShipment(null);
      setError("The tracking service is not configured.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/tracking/lookup`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ tracking_number: trackingNumber }),
        },
      );

      if (response.status === 401) {
        throw new Error("Sign in to track and save this package.");
      }

      if (!response.ok) {
        throw new Error(await getApiError(response));
      }

      const result = (await response.json()) as Shipment;
      setTrackingNumber(result.tracking_number);
      setShipment(result);
    } catch (lookupError) {
      setShipment(null);
      setError(
        lookupError instanceof Error && !(lookupError instanceof TypeError)
          ? lookupError.message
          : "We could not reach the tracking service. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mt-10 flex w-full max-w-3xl flex-col items-center">
      <form
        onSubmit={handleSubmit}
        className="w-full rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_24px_60px_rgba(15,23,42,0.10)] sm:flex sm:items-center sm:gap-3"
      >
        <label htmlFor="tracking-number" className="sr-only">
          Tracking number
        </label>
        <input
          id="tracking-number"
          name="tracking-number"
          type="text"
          inputMode="text"
          autoComplete="off"
          maxLength={100}
          required
          value={trackingNumber}
          onChange={(event) => setTrackingNumber(event.target.value)}
          aria-describedby={error ? "tracking-error" : undefined}
          placeholder="Enter a tracking number"
          className="h-14 w-full rounded-xl border-0 bg-slate-50 px-5 text-base text-slate-950 outline-none ring-1 ring-inset ring-slate-200 transition placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-blue-500 sm:flex-1"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="mt-3 inline-flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-7 text-base font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.24)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 active:translate-y-px disabled:cursor-not-allowed disabled:bg-blue-400 disabled:shadow-none disabled:active:translate-y-0 sm:mt-0 sm:w-auto"
        >
          {isLoading && (
            <span
              aria-hidden="true"
              className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
          )}
          {isLoading ? "Tracking..." : "Track Package"}
        </button>
      </form>

      <div className="w-full" aria-live="polite" aria-busy={isLoading}>
        {error && (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-left text-sm font-medium text-red-700 sm:flex-row sm:items-center sm:justify-between">
            <p id="tracking-error" role="alert">
              {error}
            </p>
            {error.startsWith("Sign in") && (
              <Link
                href="/login"
                className="shrink-0 font-semibold text-blue-700 underline underline-offset-4"
              >
                Sign in
              </Link>
            )}
          </div>
        )}

        {shipment && (
          <article className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white text-left shadow-[0_20px_50px_rgba(15,23,42,0.08)]">
            <header className="flex flex-col gap-4 border-b border-slate-100 bg-slate-50/80 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Shipment found
                </p>
                <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-950">
                  {shipment.tracking_number}
                </h2>
              </div>
              <span className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-700">
                <span className="size-2 rounded-full bg-blue-500" />
                {shipment.status}
              </span>
            </header>

            <dl className="grid gap-x-8 gap-y-6 px-5 py-6 sm:grid-cols-2 sm:px-6">
              <div>
                <dt className="text-sm font-medium text-slate-500">Carrier</dt>
                <dd className="mt-1 text-base font-semibold text-slate-950">
                  {shipment.carrier}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">
                  Estimated delivery
                </dt>
                <dd className="mt-1 text-base font-semibold text-slate-950">
                  {shipment.estimated_delivery}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-slate-500">
                  Latest update
                </dt>
                <dd className="mt-2 flex items-start gap-3 text-base font-medium text-slate-800">
                  <span className="mt-2 size-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" />
                  {shipment.latest_update}
                </dd>
              </div>
            </dl>
          </article>
        )}
      </div>
    </div>
  );
}
