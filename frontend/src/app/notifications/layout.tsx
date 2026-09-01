import type { ReactNode } from "react";

import { requireUser } from "@/lib/auth";

export default async function NotificationsLayout({
  children,
}: {
  children: ReactNode;
}) {
  await requireUser("/notifications");
  return children;
}
