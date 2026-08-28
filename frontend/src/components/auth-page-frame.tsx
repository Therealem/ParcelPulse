import Link from "next/link";
import type { ReactNode } from "react";

export function AuthPageFrame({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-[#f7f8fb] px-5 text-slate-950 sm:px-8">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-[34rem] bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.14),transparent_38%),radial-gradient(circle_at_78%_12%,rgba(14,165,233,0.12),transparent_30%)]"
      />
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between border-b border-slate-200/80 py-5">
        <Link href="/" className="flex items-center gap-3" aria-label="ParcelPulse home">
          <span className="relative grid size-10 place-items-center rounded-xl bg-blue-600 shadow-[0_8px_24px_rgba(37,99,235,0.28)]">
            <span className="h-4 w-4 rounded-[4px] border-2 border-white" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-sky-300" />
          </span>
          <span className="text-lg font-bold tracking-[-0.025em]">
            Parcel<span className="text-blue-600">Pulse</span>
          </span>
        </Link>
        <Link
          href="/"
          className="text-sm font-semibold text-slate-600 transition hover:text-blue-700"
        >
          Back home
        </Link>
      </nav>

      <section className="mx-auto grid min-h-[calc(100vh-81px)] w-full max-w-6xl items-center py-12 lg:grid-cols-[minmax(0,1fr)_28rem] lg:gap-20">
        <div className="hidden lg:block">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-600">
            One account, every delivery
          </p>
          <h2 className="mt-5 max-w-xl text-5xl font-bold leading-[1.06] tracking-[-0.05em] text-slate-950">
            Your packages stay private and organized.
          </h2>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">
            ParcelPulse keeps each account&apos;s saved shipments separate while
            bringing multiple carriers into one focused dashboard.
          </p>
        </div>

        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_28px_70px_rgba(15,23,42,0.10)] sm:p-9">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-blue-600">
            {eyebrow}
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.035em] text-slate-950">
            {title}
          </h1>
          <p className="mt-3 leading-7 text-slate-600">{description}</p>
          {children}
        </article>
      </section>
    </main>
  );
}
