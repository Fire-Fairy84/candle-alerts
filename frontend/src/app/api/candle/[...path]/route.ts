import { type NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.CANDLE_API_BASE_URL!;
const API_KEY = process.env.CANDLE_API_KEY!;

const ALLOWED_PATH_PREFIXES = ["pairs", "alerts"];
const ALLOWED_PARAMS = ["limit", "since"];

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const pathStr = path.join("/");

  // Reject paths that don't start with a known prefix
  if (!ALLOWED_PATH_PREFIXES.some((p) => pathStr.startsWith(p))) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  // Only forward whitelisted query parameters
  const url = new URL(request.url);
  const filtered = new URLSearchParams();
  ALLOWED_PARAMS.forEach((param) => {
    const value = url.searchParams.get(param);
    if (value !== null) filtered.set(param, value);
  });

  const query = filtered.toString();
  const upstream = `${BASE_URL}/api/v1/${pathStr}${query ? `?${query}` : ""}`;

  const res = await fetch(upstream, {
    headers: { "X-API-Key": API_KEY },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
