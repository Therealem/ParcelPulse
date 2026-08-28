import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthPageFrame } from "@/components/auth-page-frame";
import { getCurrentUser } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Sign In | ParcelPulse",
  description: "Sign in to view and manage your ParcelPulse shipments.",
};

function safeDestination(value: string | undefined): string {
  return value?.startsWith("/") && !value.startsWith("//")
    ? value
    : "/shipments";
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  const destination = safeDestination(next);
  const user = await getCurrentUser();

  if (user) {
    redirect(destination);
  }

  return (
    <AuthPageFrame
      eyebrow="Welcome back"
      title="Sign in to ParcelPulse"
      description="Access your private shipment dashboard and tracking history."
    >
      <AuthForm mode="login" redirectTo={destination} />
    </AuthPageFrame>
  );
}
