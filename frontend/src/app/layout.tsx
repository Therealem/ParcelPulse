import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ParcelPulse | Universal Package Tracking",
  description:
    "Track packages from UPS, USPS, FedEx, DHL, and more in one place.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
