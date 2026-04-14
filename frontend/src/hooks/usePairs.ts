"use client";

import useSWR from "swr";
import type { PairsResponse } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function usePairs() {
  const { data, error, isLoading } = useSWR<PairsResponse>(
    "/api/candle/pairs",
    fetcher,
    { refreshInterval: 60_000 },
  );
  return { pairs: data?.pairs ?? [], error, isLoading };
}
