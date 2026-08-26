"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Shipment = {
  id: number;
  tracking_number: string;
  carrier: string;
  status: string;
  estimated_delivery: string;
  latest_update: string;
  created_at: string;
  updated_at: string;
};

type DashboardState =
  | { status: "loading" }
  | { status: "success"; shipments: Shipment[] }
  | { status: "error"; message: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export function ShipmentsDashboard() {
  const [requestKey, setRequestKey] = useState(0);
  const [dashboard, setDashboard] = useState<DashboardState>({
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadShipments() {
      if (!apiBaseUrl) {
        setDashboard({
          status: "error",
          message: "The shipment service is not configured.",
        });
        return;
      }

      try {
        const response = await fetch(
          `${apiBaseUrl.replace(/\/$/, "")}/api/shipments`,
          {
            headers: { Accept: "application/json" },
            cache: "no-store",
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error("The shipment service returned an error.");
        }

        const shipments = (await response.json()) as unknown;

        if (!Array.isArray(shipments)) {
          throw new Error("The shipment service returned an invalid response.");
        }

        setDashboard({ status: "success", shipments: shipments as Shipment[] });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setDashboard({
          status: "error",
          message:
            "We could not load your shipments. Check that the backend is running, then try again.",
        });
      }
    }

    void loadShipments();

    return () => controller.abort();
  }, [requestKey]);

  function retry() {
    setDashboard({ status: "loading" });
    setRequestKey((currentKey) => currentKey + 1);
  }

  if (dashboard.status === "loading") {
    return (
      <section
        className="mt-12"
        aria-label="Loading saved shipments"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="mb-5 h-5 w-32 animate-pulse rounded-full bg-slate-200" />
        <div className="grid gap-5 md:grid-cols-2">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              aria-hidden="true"
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)]"
            >
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-6 py-5">
                <div className="space-y-2">
                  <div className="h-3 w-24 animate-pulse rounded-full bg-slate-200" />
                  <div className="h-5 w-44 animate-pulse rounded-full bg-slate-200" />
                </div>
                <div className="h-8 w-24 animate-pulse rounded-full bg-blue-100" />
              </div>
              <div className="grid grid-cols-2 gap-6 p-6">
                <div className="h-12 animate-pulse rounded-lg bg-slate-100" />
                <div className="h-12 animate-pulse rounded-lg bg-slate-100" />
                <div className="col-span-2 h-16 animate-pulse rounded-lg bg-slate-100" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (dashboard.status === "error") {
    return (
      <section
        role="alert"
        className="mt-12 rounded-2xl border border-red-200 bg-white px-6 py-10 text-center shadow-[0_16px_40px_rgba(15,23,42,0.06)] sm:px-10"
      >
        <span
          aria-hidden="true"
          className="mx-auto grid size-12 place-items-center rounded-full bg-red-50 text-xl font-bold text-red-600"
        >
          !
        </span>
        <h2 className="mt-5 text-xl font-bold tracking-tight text-slate-950">
          Shipments unavailable
        </h2>
        <p className="mx-auto mt-2 max-w-lg leading-7 text-slate-600">
          {dashboard.message}
        </p>
        <button
          type="button"
          onClick={retry}
          className="mt-6 inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 active:translate-y-px"
        >
          Try again
        </button>
      </section>
    );
  }

  if (dashboard.shipments.length === 0) {
    return (
      <section className="mt-12 rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-[0_16px_40px_rgba(15,23,42,0.06)] sm:px-10">
        <span
          aria-hidden="true"
          className="mx-auto grid size-14 place-items-center rounded-2xl bg-blue-50"
        >
          <span className="size-5 rounded-md border-2 border-blue-600" />
        </span>
        <h2 className="mt-5 text-xl font-bold tracking-tight text-slate-950">
          No saved shipments yet
        </h2>
        <p className="mx-auto mt-2 max-w-lg leading-7 text-slate-600">
          Track a package from the home page and it will appear here automatically.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 active:translate-y-px"
        >
          Track your first package
        </Link>
      </section>
    );
  }

  return (
    <section className="mt-12" aria-labelledby="saved-shipments-heading">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-blue-600">
            Saved packages
          </p>
          <h2
            id="saved-shipments-heading"
            className="mt-1 text-2xl font-bold tracking-tight text-slate-950"
          >
            Your shipments
          </h2>
        </div>
        <p className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-600 shadow-sm">
          {dashboard.shipments.length}{" "}
          {dashboard.shipments.length === 1 ? "shipment" : "shipments"}
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {dashboard.shipments.map((shipment) => (
          <Link
            key={shipment.id}
            href={`/shipments/${shipment.id}`}
            aria-label={`View details for shipment ${shipment.tracking_number}`}
            className="group block rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600"
          >
            <article className="h-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)] transition duration-200 group-hover:-translate-y-0.5 group-hover:border-blue-200 group-hover:shadow-[0_20px_48px_rgba(15,23,42,0.09)]">
              <header className="flex flex-col gap-4 border-b border-slate-100 bg-slate-50/80 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Tracking number
                  </p>
                  <h3 className="mt-1 break-all text-lg font-bold tracking-tight text-slate-950 transition group-hover:text-blue-700">
                    {shipment.tracking_number}
                  </h3>
                </div>
                <span className="inline-flex w-fit shrink-0 items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-700">
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
                  <dd className="mt-2 flex items-start gap-3 text-base font-medium leading-7 text-slate-800">
                    <span className="mt-2.5 size-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" />
                    {shipment.latest_update}
                  </dd>
                </div>
              </dl>
              <div className="border-t border-slate-100 px-5 py-4 text-sm font-semibold text-blue-700 sm:px-6">
                View shipment details <span aria-hidden="true">→</span>
              </div>
            </article>
          </Link>
        ))}
      </div>
    </section>
  );
}
