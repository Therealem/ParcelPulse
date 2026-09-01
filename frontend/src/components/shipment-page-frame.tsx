import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/logout-button";
import { NotificationBell } from "@/components/notification-bell";

export function ShipmentPageFrame({ children }: { children: ReactNode }) {
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
            href="/shipments"
            className="hidden h-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 px-4 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur transition hover:border-blue-200 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 sm:inline-flex"
          >
            Saved Shipments
          </Link>
          <NotificationBell />
          <LogoutButton />
        </div>
      </nav>

      {children}
    </main>
  );
}
