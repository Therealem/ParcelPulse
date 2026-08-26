import { ShipmentPageFrame } from "@/components/shipment-page-frame";

export default function ShipmentDetailLoading() {
  return (
    <ShipmentPageFrame>
      <section
        aria-label="Loading shipment details"
        aria-live="polite"
        aria-busy="true"
        className="mx-auto w-full max-w-6xl pb-20 pt-12"
      >
        <div className="h-4 w-44 animate-pulse rounded-full bg-slate-200" />
        <div className="mt-9 flex items-end justify-between gap-6">
          <div className="space-y-3">
            <div className="h-4 w-24 animate-pulse rounded-full bg-blue-100" />
            <div className="h-10 w-72 max-w-full animate-pulse rounded-xl bg-slate-200" />
          </div>
          <div className="hidden h-10 w-28 animate-pulse rounded-full bg-blue-100 sm:block" />
        </div>
        <div className="mt-9 grid gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <div className="space-y-6">
            <div className="h-64 animate-pulse rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)]" />
            <div className="h-28 animate-pulse rounded-2xl bg-emerald-50" />
          </div>
          <div className="h-[34rem] animate-pulse rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.06)]" />
        </div>
      </section>
    </ShipmentPageFrame>
  );
}
