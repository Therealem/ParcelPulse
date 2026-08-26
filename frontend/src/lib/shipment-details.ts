import { cache } from "react";

export type TrackingEvent = {
  id: number;
  shipment_id: number;
  status: string;
  description: string;
  location: string | null;
  event_time: string;
  created_at: string;
};

export type ShipmentDetail = {
  id: number;
  tracking_number: string;
  carrier: string;
  status: string;
  estimated_delivery: string;
  latest_update: string;
  created_at: string;
  updated_at: string;
  tracking_events: TrackingEvent[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export const getShipmentDetail = cache(
  async (shipmentId: number): Promise<ShipmentDetail | null> => {
    if (!apiBaseUrl) {
      throw new Error("The shipment service is not configured.");
    }

    const response = await fetch(
      `${apiBaseUrl.replace(/\/$/, "")}/api/shipments/${shipmentId}`,
      {
        headers: { Accept: "application/json" },
        cache: "no-store",
      },
    );

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error("The shipment service returned an error.");
    }

    return (await response.json()) as ShipmentDetail;
  },
);
