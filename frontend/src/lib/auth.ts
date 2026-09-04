import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export type AuthenticatedUser = {
  id: number;
  email: string;
  created_at: string;
  updated_at: string;
};

const apiBaseUrl = (
  process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function getRequestCookieHeader(): Promise<string> {
  return (await cookies()).toString();
}

export const getCurrentUser = cache(
  async (): Promise<AuthenticatedUser | null> => {
    const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
      headers: {
        Accept: "application/json",
        Cookie: await getRequestCookieHeader(),
      },
      cache: "no-store",
    });

    if (response.status === 401) {
      return null;
    }

    if (!response.ok) {
      throw new Error("The authentication service returned an error.");
    }

    return (await response.json()) as AuthenticatedUser;
  },
);

export async function requireUser(
  destination = "/shipments",
): Promise<AuthenticatedUser> {
  const user = await getCurrentUser();

  if (!user) {
    redirect(`/login?next=${encodeURIComponent(destination)}`);
  }

  return user;
}
