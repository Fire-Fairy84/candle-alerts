"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCandles } from "@/hooks/useCandles";
import type { TradingPair } from "@/lib/types";

interface PairCardProps {
  pair: TradingPair;
}

function formatPrice(price: number): string {
  if (price >= 1000) return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (price >= 1) return price.toFixed(2);
  return price.toFixed(4);
}

export function PairCard({ pair }: PairCardProps) {
  const { candles, isLoading } = useCandles(pair.id, 2);

  const last = candles.length > 0 ? candles[candles.length - 1] : null;
  const prev = candles.length > 1 ? candles[candles.length - 2] : null;

  const price = last?.close ?? null;
  const change = price && prev ? ((price - prev.close) / prev.close) * 100 : null;
  const rsi = last?.indicators?.rsi ?? null;

  const changeColor = change === null
    ? "text-muted-foreground"
    : change >= 0
      ? "text-green-600"
      : "text-red-500";

  return (
    <Link href={`/pairs/${pair.id}`}>
      <Card className="hover:bg-accent transition-colors cursor-pointer h-full">
        <CardHeader className="pb-1">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{pair.symbol}</CardTitle>
            <div className="flex gap-1.5">
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{pair.exchange.slug}</Badge>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{pair.timeframe}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-2">
          {isLoading ? (
            <div className="h-10 flex items-center">
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          ) : price !== null ? (
            <div className="space-y-1">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-semibold tabular-nums">
                  {formatPrice(price)}
                </span>
                {change !== null && (
                  <span className={`text-sm font-medium ${changeColor}`}>
                    {change >= 0 ? "+" : ""}{change.toFixed(2)}%
                  </span>
                )}
              </div>
              {rsi !== null && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>RSI</span>
                  <span className={
                    rsi < 30 ? "text-red-500 font-medium" :
                    rsi > 70 ? "text-green-600 font-medium" :
                    "text-foreground"
                  }>
                    {rsi.toFixed(1)}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">No data</span>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
