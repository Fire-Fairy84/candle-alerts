"use client";

import useSWR from "swr";
import type { CandlesResponse } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useCandles(pairId: number, limit = 500) {
  const { data, error, isLoading } = useSWR<CandlesResponse>(
    `/api/candle/pairs/${pairId}/candles?limit=${limit}`,
    fetcher,
    { refreshInterval: 300_000 },
  );
  return { data, candles: data?.candles ?? [], error, isLoading };
}
