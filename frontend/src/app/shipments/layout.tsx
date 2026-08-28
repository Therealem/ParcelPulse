import type { ReactNode } from "react";

import { requireUser } from "@/lib/auth";

export default async function ShipmentsLayout({
  children,
}: {
  children: ReactNode;
}) {
  await requireUser("/shipments");
  return children;
}
