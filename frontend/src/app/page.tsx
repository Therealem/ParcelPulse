import { TrackingLookup } from "@/components/tracking-lookup";

const carriers = ["UPS", "USPS", "FedEx", "DHL"];

export default function Home() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-[#f7f8fb] px-5 text-slate-950 sm:px-8">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-[34rem] bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.13),transparent_38%),radial-gradient(circle_at_78%_12%,rgba(14,165,233,0.12),transparent_30%)]"
      />

      <nav
        aria-label="Primary navigation"
        className="mx-auto flex w-full max-w-6xl items-center justify-between border-b border-slate-200/80 py-5"
      >
        <a href="#" className="flex items-center gap-3" aria-label="ParcelPulse home">
          <span className="relative grid size-10 place-items-center rounded-xl bg-blue-600 shadow-[0_8px_24px_rgba(37,99,235,0.28)]">
            <span className="h-4 w-4 rounded-[4px] border-2 border-white" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-sky-300" />
          </span>
          <span className="text-lg font-bold tracking-[-0.025em]">
            Parcel<span className="text-blue-600">Pulse</span>
          </span>
        </a>

        <span className="hidden text-sm font-medium text-slate-500 sm:block">
          One search. Every carrier.
        </span>
      </nav>

      <section className="mx-auto flex w-full max-w-5xl flex-col items-center pb-20 pt-20 text-center sm:pt-28 lg:pt-32">
        <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-4 py-2 text-sm font-semibold text-blue-700 shadow-sm backdrop-blur">
          <span className="size-2 rounded-full bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.12)]" />
          Multi-carrier tracking, simplified
        </div>

        <h1 className="max-w-4xl text-balance text-5xl font-bold leading-[1.02] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-7xl">
          Track every package. <span className="text-blue-600">One place.</span>
        </h1>

        <p className="mt-7 max-w-2xl text-pretty text-lg leading-8 text-slate-600 sm:text-xl">
          Follow packages from UPS, USPS, FedEx, DHL, and more without jumping
          between carrier websites.
        </p>

        <TrackingLookup />

        <div className="mt-7 flex flex-wrap items-center justify-center gap-x-5 gap-y-3 text-sm text-slate-500">
          <span className="font-medium">Built to support</span>
          {carriers.map((carrier) => (
            <span
              key={carrier}
              className="rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 font-semibold text-slate-700"
            >
              {carrier}
            </span>
          ))}
          <span className="font-medium text-slate-400">and more</span>
        </div>
      </section>
    </main>
  );
}
