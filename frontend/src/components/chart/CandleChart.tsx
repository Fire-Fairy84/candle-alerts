"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  CandlestickSeries,
  LineSeries,
} from "lightweight-charts";
import { useCandles } from "@/hooks/useCandles";
import { ChartSkeleton } from "./ChartSkeleton";

interface CandleChartProps {
  pairId: number;
}

export function CandleChart({ pairId }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema9Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ema21Ref = useRef<ISeriesApi<"Line"> | null>(null);

  const { candles, isLoading, error } = useCandles(pairId, 500);

  // Create chart once the container is mounted
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: "transparent" },
        textColor: "#9ca3af",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      timeScale: { timeVisible: true },
    });

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    ema9Ref.current = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    ema21Ref.current = chart.addSeries(LineSeries, {
      color: "#3b82f6",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      ema9Ref.current = null;
      ema21Ref.current = null;
    };
  });

  // Update data when candles change
  useEffect(() => {
    if (!candleSeriesRef.current || !ema9Ref.current || !ema21Ref.current) return;
    if (candles.length === 0) return;

    const sorted = [...candles].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );

    candleSeriesRef.current.setData(
      sorted.map((c) => ({
        time: (new Date(c.timestamp).getTime() / 1000) as unknown as string,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );

    ema9Ref.current.setData(
      sorted
        .filter((c) => c.indicators.ema_9 !== null)
        .map((c) => ({
          time: (new Date(c.timestamp).getTime() / 1000) as unknown as string,
          value: c.indicators.ema_9!,
        })),
    );

    ema21Ref.current.setData(
      sorted
        .filter((c) => c.indicators.ema_21 !== null)
        .map((c) => ({
          time: (new Date(c.timestamp).getTime() / 1000) as unknown as string,
          value: c.indicators.ema_21!,
        })),
    );

    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  if (error) return <p className="text-destructive text-sm">Failed to load chart data.</p>;

  return (
    <div className="relative">
      {isLoading && (
        <div className="absolute inset-0 z-10">
          <ChartSkeleton />
        </div>
      )}
      <div ref={containerRef} className="h-[500px] w-full rounded-xl overflow-hidden" />
    </div>
  );
}
