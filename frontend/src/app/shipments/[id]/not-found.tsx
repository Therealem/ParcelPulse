import Link from "next/link";

import { ShipmentPageFrame } from "@/components/shipment-page-frame";

export default function ShipmentDetailNotFound() {
  return (
    <ShipmentPageFrame>
      <section className="mx-auto flex w-full max-w-3xl flex-col items-center pb-24 pt-20 text-center sm:pt-28">
        <span
          aria-hidden="true"
          className="grid size-14 place-items-center rounded-2xl bg-blue-50 text-lg font-bold text-blue-700 ring-1 ring-inset ring-blue-100"
        >
          404
        </span>
        <p className="mt-6 text-sm font-semibold uppercase tracking-[0.14em] text-blue-600">
          Shipment not found
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.035em] text-slate-950 sm:text-4xl">
          This package is not in ParcelPulse
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-slate-600">
          The shipment may have been removed, or the link may contain an invalid
          shipment ID.
        </p>
        <Link
          href="/shipments"
          className="mt-8 inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)] transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Back to Saved Shipments
        </Link>
      </section>
    </ShipmentPageFrame>
  );
}
