import type { Metadata } from "next";
import Link from "next/link";

import { NotificationsView } from "@/components/notifications-view";
import { ShipmentPageFrame } from "@/components/shipment-page-frame";

export const metadata: Metadata = {
  title: "Notifications | ParcelPulse",
  description: "Review important updates about your saved shipments.",
};

export default function NotificationsPage() {
  return (
    <ShipmentPageFrame>
      <section className="mx-auto w-full max-w-4xl pb-20 pt-10 sm:pt-14">
        <Link
          href="/shipments"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600"
        >
          <span aria-hidden="true">&larr;</span>
          Back to Saved Shipments
        </Link>

        <header className="mt-8 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-4 py-2 text-sm font-semibold text-blue-700 shadow-sm backdrop-blur">
            <span className="size-2 rounded-full bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.12)]" />
            Delivery alerts
          </div>
          <h1 className="mt-6 text-balance text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">
            Shipment <span className="text-blue-600">notifications.</span>
          </h1>
          <p className="mt-4 text-lg leading-8 text-slate-600">
            Important changes appear here without turning every carrier scan
            into noise.
          </p>
        </header>

        <NotificationsView />
      </section>
    </ShipmentPageFrame>
  );
}
