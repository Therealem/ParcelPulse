"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

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

type RefreshFeedback = {
  shipmentId: number;
  status: "success" | "error";
  message: string;
};

type SortOption = "newest" | "oldest" | "estimated-delivery";

const emptyShipments: Shipment[] = [];

async function requestShipments(signal?: AbortSignal): Promise<Shipment[]> {
  const response = await fetch("/api/shipments", {
    headers: { Accept: "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (response.status === 401) {
    throw new Error("AUTH_REQUIRED");
  }

  if (!response.ok) {
    throw new Error("The shipment service returned an error.");
  }

  const shipments = (await response.json()) as unknown;
  if (!Array.isArray(shipments)) {
    throw new Error("The shipment service returned an invalid response.");
  }

  return shipments as Shipment[];
}

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

function dateValue(value: string): number {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function normalizeTrackingNumber(value: string): string {
  return value.normalize("NFKC").replace(/[^a-z0-9]/gi, "").toUpperCase();
}

export function ShipmentsDashboard({
  initialNotice,
  refreshToken,
}: {
  initialNotice?: string;
  refreshToken?: string;
}) {
  const router = useRouter();
  const { bfcacheId } = router;
  const [requestKey, setRequestKey] = useState(0);
  const [dashboard, setDashboard] = useState<DashboardState>({
    status: "loading",
  });
  const [search, setSearch] = useState("");
  const [carrier, setCarrier] = useState("all");
  const [shipmentStatus, setShipmentStatus] = useState("all");
  const [sort, setSort] = useState<SortOption>("newest");
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [refreshFeedback, setRefreshFeedback] =
    useState<RefreshFeedback | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadShipments() {
      try {
        const shipments = await requestShipments(controller.signal);
        setDashboard({ status: "success", shipments });
        setCarrier((currentCarrier) =>
          currentCarrier === "all" ||
          shipments.some(
            (shipment) => shipment.carrier === currentCarrier,
          )
            ? currentCarrier
            : "all",
        );
        setShipmentStatus((currentStatus) =>
          currentStatus === "all" ||
          shipments.some((shipment) => shipment.status === currentStatus)
            ? currentStatus
            : "all",
        );
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        if (error instanceof Error && error.message === "AUTH_REQUIRED") {
          router.replace("/login?next=%2Fshipments");
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
  }, [bfcacheId, refreshToken, requestKey, router]);

  const shipments =
    dashboard.status === "success" ? dashboard.shipments : emptyShipments;

  const carrierOptions = useMemo(
    () => [...new Set(shipments.map((shipment) => shipment.carrier))].sort(),
    [shipments],
  );
  const statusOptions = useMemo(
    () => [...new Set(shipments.map((shipment) => shipment.status))].sort(),
    [shipments],
  );
  const visibleShipments = useMemo(() => {
    const normalizedSearch = normalizeTrackingNumber(search);

    return shipments
      .filter((shipment) => {
        const matchesSearch = normalizeTrackingNumber(
          shipment.tracking_number,
        ).includes(normalizedSearch);
        const matchesCarrier =
          carrier === "all" || shipment.carrier === carrier;
        const matchesStatus =
          shipmentStatus === "all" || shipment.status === shipmentStatus;

        return matchesSearch && matchesCarrier && matchesStatus;
      })
      .sort((first, second) => {
        if (sort === "oldest") {
          return (
            dateValue(first.created_at) - dateValue(second.created_at) ||
            first.id - second.id
          );
        }

        if (sort === "estimated-delivery") {
          return (
            dateValue(first.estimated_delivery) -
              dateValue(second.estimated_delivery) ||
            second.id - first.id
          );
        }

        return (
          dateValue(second.created_at) - dateValue(first.created_at) ||
          second.id - first.id
        );
      });
  }, [carrier, search, shipmentStatus, shipments, sort]);

  function retry() {
    setDashboard({ status: "loading" });
    setRequestKey((currentKey) => currentKey + 1);
  }

  function clearFilters() {
    setSearch("");
    setCarrier("all");
    setShipmentStatus("all");
    setSort("newest");
  }

  async function refreshShipment(shipment: Shipment) {
    setRefreshingId(shipment.id);
    setRefreshFeedback(null);

    try {
      const response = await fetch(
        `/api/shipments/${shipment.id}/refresh`,
        {
          method: "POST",
          credentials: "include",
        },
      );

      if (response.status === 401) {
        router.replace("/login?next=%2Fshipments");
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

      const refreshed = (await response.json()) as Shipment;
      setDashboard((currentDashboard) => {
        if (currentDashboard.status !== "success") {
          return currentDashboard;
        }

        return {
          status: "success",
          shipments: currentDashboard.shipments.map((currentShipment) =>
            currentShipment.id === shipment.id
              ? { ...currentShipment, ...refreshed }
              : currentShipment,
          ),
        };
      });
      setRefreshFeedback({
        shipmentId: shipment.id,
        status: "success",
        message: "Shipment refreshed. Tracking history is up to date.",
      });
    } catch (error) {
      setRefreshFeedback({
        shipmentId: shipment.id,
        status: "error",
        message:
          error instanceof Error && !(error instanceof TypeError)
            ? error.message
            : "We could not reach the tracking service. Please try again.",
      });
    } finally {
      setRefreshingId(null);
    }
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
      <div className="mt-12">
        {initialNotice && (
          <p
            role="status"
            className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800"
          >
            {initialNotice}
          </p>
        )}
        <section className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-[0_16px_40px_rgba(15,23,42,0.06)] sm:px-10">
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
            Track a package from the home page and it will appear here
            automatically.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 active:translate-y-px"
          >
            Track your first package
          </Link>
        </section>
      </div>
    );
  }

  return (
    <section className="mt-12" aria-labelledby="saved-shipments-heading">
      {initialNotice && (
        <p
          role="status"
          className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800"
        >
          {initialNotice}
        </p>
      )}

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
          {visibleShipments.length === dashboard.shipments.length
            ? `${dashboard.shipments.length} ${
                dashboard.shipments.length === 1 ? "shipment" : "shipments"
              }`
            : `${visibleShipments.length} of ${dashboard.shipments.length}`}
        </p>
      </div>

      <div className="mb-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_12px_32px_rgba(15,23,42,0.05)] sm:p-5 lg:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,0.8fr))]">
        <label>
          <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Search tracking number
          </span>
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Enter all or part of a number"
            className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label>
          <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Carrier
          </span>
          <select
            value={carrier}
            onChange={(event) => setCarrier(event.target.value)}
            className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          >
            <option value="all">All carriers</option>
            {carrierOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Status
          </span>
          <select
            value={shipmentStatus}
            onChange={(event) => setShipmentStatus(event.target.value)}
            className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          >
            <option value="all">All statuses</option>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Sort
          </span>
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortOption)}
            className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          >
            <option value="newest">Newest saved</option>
            <option value="oldest">Oldest saved</option>
            <option value="estimated-delivery">Estimated delivery</option>
          </select>
        </label>
      </div>

      {visibleShipments.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 px-6 py-12 text-center">
          <h3 className="text-lg font-bold text-slate-950">
            No shipments match those filters
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Try a different tracking number, carrier, or status.
          </p>
          <button
            type="button"
            onClick={clearFilters}
            className="mt-5 inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {visibleShipments.map((shipment) => {
            const feedback =
              refreshFeedback?.shipmentId === shipment.id
                ? refreshFeedback
                : null;
            const isRefreshing = refreshingId === shipment.id;

            return (
              <article
                key={shipment.id}
                className="group relative h-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)] transition duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-[0_20px_48px_rgba(15,23,42,0.09)]"
              >
                <Link
                  href={`/shipments/${shipment.id}`}
                  aria-label={`View details for shipment ${shipment.tracking_number}`}
                  className="absolute inset-0 z-10 rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  <span className="sr-only">View shipment details</span>
                </Link>

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
                    <dt className="text-sm font-medium text-slate-500">
                      Carrier
                    </dt>
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

                <div className="flex items-center justify-between gap-4 border-t border-slate-100 px-5 py-4 sm:px-6">
                  <span className="text-sm font-semibold text-blue-700">
                    View shipment details <span aria-hidden="true">→</span>
                  </span>
                  <button
                    type="button"
                    disabled={refreshingId !== null}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void refreshShipment(shipment);
                    }}
                    className="relative z-20 inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:text-slate-400"
                  >
                    {isRefreshing && (
                      <span
                        aria-hidden="true"
                        className="size-3.5 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600"
                      />
                    )}
                    {isRefreshing ? "Refreshing..." : "Refresh"}
                  </button>
                </div>

                {feedback && (
                  <p
                    role={feedback.status === "error" ? "alert" : "status"}
                    className={`relative z-20 border-t px-5 py-3 text-sm font-semibold sm:px-6 ${
                      feedback.status === "success"
                        ? "border-emerald-100 bg-emerald-50 text-emerald-800"
                        : "border-red-100 bg-red-50 text-red-700"
                    }`}
                  >
                    {feedback.message}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
