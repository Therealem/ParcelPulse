import type { Metadata } from "next";
import Link from "next/link";

import { ShipmentsDashboard } from "@/components/shipments-dashboard";
import { LogoutButton } from "@/components/logout-button";
import { NotificationBell } from "@/components/notification-bell";

export const metadata: Metadata = {
  title: "Saved Shipments | ParcelPulse",
  description: "View every package saved to your ParcelPulse dashboard.",
};

export default async function ShipmentsPage({
  searchParams,
}: {
  searchParams: Promise<{ deleted?: string }>;
}) {
  const { deleted } = await searchParams;

  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-[#f7f8fb] px-5 text-slate-950 sm:px-8">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-[30rem] bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.13),transparent_38%),radial-gradient(circle_at_78%_12%,rgba(14,165,233,0.12),transparent_30%)]"
      />

      <nav
        aria-label="Primary navigation"
        className="mx-auto flex w-full max-w-6xl items-center justify-between border-b border-slate-200/80 py-5"
      >
        <Link href="/" className="flex items-center gap-3" aria-label="ParcelPulse home">
          <span className="relative grid size-10 place-items-center rounded-xl bg-blue-600 shadow-[0_8px_24px_rgba(37,99,235,0.28)]">
            <span className="h-4 w-4 rounded-[4px] border-2 border-white" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-sky-300" />
          </span>
          <span className="hidden text-lg font-bold tracking-[-0.025em] sm:inline">
            Parcel<span className="text-blue-600">Pulse</span>
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="hidden h-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 px-4 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 sm:inline-flex"
          >
            Track a package
          </Link>
          <NotificationBell />
          <LogoutButton />
        </div>
      </nav>

      <section className="mx-auto w-full max-w-6xl pb-20 pt-14 sm:pt-20">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-4 py-2 text-sm font-semibold text-blue-700 shadow-sm backdrop-blur">
            <span className="size-2 rounded-full bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.12)]" />
            Shipment dashboard
          </div>
          <h1 className="mt-6 text-balance text-4xl font-bold leading-tight tracking-[-0.045em] text-slate-950 sm:text-5xl lg:text-6xl">
            Every delivery, <span className="text-blue-600">at a glance.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-pretty text-lg leading-8 text-slate-600">
            Review the latest status, carrier, and delivery estimate for every
            package you have tracked with ParcelPulse.
          </p>
        </div>

        <ShipmentsDashboard
          refreshToken={deleted}
          initialNotice={
            deleted
              ? "Shipment deleted successfully. Its tracking history was also removed."
              : undefined
          }
        />
      </section>
    </main>
  );
}
