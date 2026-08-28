import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthPageFrame } from "@/components/auth-page-frame";
import { getCurrentUser } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Create Account | ParcelPulse",
  description: "Create a ParcelPulse account to save and manage shipments.",
};

export default async function RegisterPage() {
  const user = await getCurrentUser();

  if (user) {
    redirect("/shipments");
  }

  return (
    <AuthPageFrame
      eyebrow="Get started"
      title="Create your account"
      description="Save packages from every supported carrier in one private dashboard."
    >
      <AuthForm mode="register" />
    </AuthPageFrame>
  );
}
