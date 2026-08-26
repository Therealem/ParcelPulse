"use client";

import Link from "next/link";

import { ShipmentPageFrame } from "@/components/shipment-page-frame";

export default function ShipmentDetailError({ retry }: { retry: () => void }) {
  return (
    <ShipmentPageFrame>
      <section
        role="alert"
        className="mx-auto flex w-full max-w-3xl flex-col items-center pb-24 pt-20 text-center sm:pt-28"
      >
        <span
          aria-hidden="true"
          className="grid size-14 place-items-center rounded-full bg-red-50 text-xl font-bold text-red-600 ring-1 ring-inset ring-red-100"
        >
          !
        </span>
        <p className="mt-6 text-sm font-semibold uppercase tracking-[0.14em] text-red-600">
          Connection error
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.035em] text-slate-950 sm:text-4xl">
          Shipment details are unavailable
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-slate-600">
          We could not reach the shipment service. Check that the backend is
          running, then try again.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={retry}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Try again
          </button>
          <Link
            href="/shipments"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Back to Saved Shipments
          </Link>
        </div>
      </section>
    </ShipmentPageFrame>
  );
}
