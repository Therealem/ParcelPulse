import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ShipmentActions } from "@/components/shipment-actions";
import { ShipmentPageFrame } from "@/components/shipment-page-frame";
import { getShipmentDetail } from "@/lib/shipment-details";

type ShipmentPageProps = {
  params: Promise<{ id: string }>;
};

function parseShipmentId(value: string): number | null {
  const shipmentId = Number(value);
  return Number.isSafeInteger(shipmentId) && shipmentId > 0
    ? shipmentId
    : null;
}

function formatEventTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Chicago",
    timeZoneName: "short",
  }).format(new Date(value));
}

export async function generateMetadata({
  params,
}: ShipmentPageProps): Promise<Metadata> {
  const { id } = await params;
  const shipmentId = parseShipmentId(id);

  if (shipmentId === null) {
    return {
      title: "Shipment Not Found | ParcelPulse",
      description: "The requested ParcelPulse shipment could not be found.",
      robots: { index: false },
    };
  }

  const shipment = await getShipmentDetail(shipmentId);

  if (shipment === null) {
    return {
      title: "Shipment Not Found | ParcelPulse",
      description: "The requested ParcelPulse shipment could not be found.",
      robots: { index: false },
    };
  }

  const title = `${shipment.tracking_number} | ParcelPulse`;
  const description = `${shipment.carrier} shipment ${shipment.tracking_number} is ${shipment.status}.`;

  return {
    title,
    description,
    openGraph: { title, description, images: [] },
    twitter: { card: "summary", title, description, images: [] },
  };
}

export default async function ShipmentDetailPage({
  params,
}: ShipmentPageProps) {
  const { id } = await params;
  const shipmentId = parseShipmentId(id);

  if (shipmentId === null) {
    notFound();
  }

  const shipment = await getShipmentDetail(shipmentId);

  if (shipment === null) {
    notFound();
  }

  return (
    <ShipmentPageFrame>
      <section className="mx-auto w-full max-w-6xl pb-20 pt-10 sm:pt-14">
        <Link
          href="/shipments"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600"
        >
          <span aria-hidden="true">←</span>
          Back to Saved Shipments
        </Link>

        <header className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-blue-600">
              {shipment.carrier} shipment
            </p>
            <h1 className="mt-2 break-all text-3xl font-bold tracking-[-0.035em] text-slate-950 sm:text-4xl lg:text-5xl">
              {shipment.tracking_number}
            </h1>
          </div>
          <div className="flex flex-col items-start gap-4 lg:items-end">
            <span className="inline-flex w-fit shrink-0 items-center gap-2 rounded-full bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 ring-1 ring-inset ring-blue-100">
              <span className="size-2.5 rounded-full bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.12)]" />
              {shipment.status}
            </span>
            <ShipmentActions
              shipmentId={shipment.id}
              trackingNumber={shipment.tracking_number}
            />
          </div>
        </header>

        <div className="mt-9 grid gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-start">
          <div className="space-y-6">
            <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)]">
              <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-5 sm:px-6">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Shipment summary
                </p>
                <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">
                  Delivery details
                </h2>
              </div>
              <dl className="grid gap-6 px-5 py-6 sm:grid-cols-2 sm:px-6 lg:grid-cols-1 xl:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-slate-500">Carrier</dt>
                  <dd className="mt-1 text-base font-semibold text-slate-950">
                    {shipment.carrier}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-slate-500">
                    Current status
                  </dt>
                  <dd className="mt-1 text-base font-semibold text-slate-950">
                    {shipment.status}
                  </dd>
                </div>
                <div className="sm:col-span-2 lg:col-span-1 xl:col-span-2">
                  <dt className="text-sm font-medium text-slate-500">
                    Estimated delivery
                  </dt>
                  <dd className="mt-1 text-xl font-bold tracking-tight text-blue-700">
                    {shipment.estimated_delivery}
                  </dd>
                </div>
              </dl>
            </article>

            <article className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-5 py-5 shadow-[0_12px_32px_rgba(15,23,42,0.04)] sm:px-6">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                Latest update
              </p>
              <p className="mt-2 flex items-start gap-3 font-semibold leading-7 text-slate-900">
                <span className="mt-2.5 size-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" />
                {shipment.latest_update}
              </p>
            </article>
          </div>

          <section
            aria-labelledby="tracking-history-heading"
            className="rounded-2xl border border-slate-200 bg-white px-5 py-6 shadow-[0_16px_40px_rgba(15,23,42,0.06)] sm:px-7 sm:py-7"
          >
            <div className="border-b border-slate-100 pb-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-600">
                Live journey
              </p>
              <h2
                id="tracking-history-heading"
                className="mt-1 text-2xl font-bold tracking-tight text-slate-950"
              >
                Tracking history
              </h2>
            </div>

            {shipment.tracking_events.length > 0 ? (
              <ol className="mt-7">
                {shipment.tracking_events.map((event, index) => (
                  <li
                    key={event.id}
                    className="relative grid grid-cols-[2rem_minmax(0,1fr)] gap-4 pb-8 last:pb-0"
                  >
                    {index < shipment.tracking_events.length - 1 && (
                      <span
                        aria-hidden="true"
                        className="absolute bottom-0 left-[0.9375rem] top-7 w-px bg-slate-200"
                      />
                    )}
                    <span
                      aria-hidden="true"
                      className={`relative z-10 mt-1 grid size-8 place-items-center rounded-full ${
                        index === 0
                          ? "bg-blue-600 shadow-[0_0_0_6px_rgba(59,130,246,0.10)]"
                          : "border-2 border-slate-300 bg-white"
                      }`}
                    >
                      <span
                        className={`size-2 rounded-full ${
                          index === 0 ? "bg-white" : "bg-slate-400"
                        }`}
                      />
                    </span>
                    <div>
                      <time
                        dateTime={event.event_time}
                        className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-400"
                      >
                        {formatEventTime(event.event_time)}
                      </time>
                      <h3 className="mt-1 text-lg font-bold tracking-tight text-slate-950">
                        {event.status}
                      </h3>
                      <p className="mt-1 leading-7 text-slate-600">
                        {event.description}
                      </p>
                      {event.location && (
                        <p className="mt-2 text-sm font-semibold text-slate-500">
                          {event.location}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="py-10 text-center">
                <p className="font-semibold text-slate-900">
                  No tracking events yet
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  New carrier updates will appear here when they are available.
                </p>
              </div>
            )}
          </section>
        </div>
      </section>
    </ShipmentPageFrame>
  );
}
