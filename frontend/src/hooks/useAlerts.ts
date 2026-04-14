"use client";

import useSWR from "swr";
import type { AlertsResponse } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useAlerts(limit = 50) {
  const { data, error, isLoading } = useSWR<AlertsResponse>(
    `/api/candle/alerts?limit=${limit}`,
    fetcher,
    { refreshInterval: 60_000 },
  );
  return { alerts: data?.alerts ?? [], error, isLoading };
}
