import type { AlertsResponse, CandlesResponse, PairsResponse } from "@/lib/types";

const BASE_URL = process.env.CANDLE_API_BASE_URL!;
const API_KEY = process.env.CANDLE_API_KEY!;

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "X-API-Key": API_KEY },
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function getPairs(): Promise<PairsResponse> {
  return apiFetch<PairsResponse>("/api/v1/pairs");
}

export async function getCandles(
  pairId: number,
  limit = 100,
): Promise<CandlesResponse> {
  return apiFetch<CandlesResponse>(`/api/v1/pairs/${pairId}/candles?limit=${limit}`);
}

export async function getAlerts(limit = 50): Promise<AlertsResponse> {
  return apiFetch<AlertsResponse>(`/api/v1/alerts?limit=${limit}`);
}
