"use client";

import { useAlerts } from "@/hooks/useAlerts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { AlertBadge } from "./AlertBadge";

const RULE_CATEGORY: Record<string, { label: string; className: string }> = {
  "EMA Crossover 9/21": {
    label: "Trend",
    className: "bg-blue-500/15 text-blue-600 hover:bg-blue-500/15",
  },
  "RSI Oversold": {
    label: "Momentum",
    className: "bg-orange-500/15 text-orange-600 hover:bg-orange-500/15",
  },
  "RSI Overbought": {
    label: "Momentum",
    className: "bg-orange-500/15 text-orange-600 hover:bg-orange-500/15",
  },
  "Price Above VWAP": {
    label: "Trend",
    className: "bg-blue-500/15 text-blue-600 hover:bg-blue-500/15",
  },
  "Volume Spike 2x": {
    label: "Volume",
    className: "bg-purple-500/15 text-purple-600 hover:bg-purple-500/15",
  },
};

const DEFAULT_CATEGORY = {
  label: "Signal",
  className: "bg-gray-500/15 text-gray-600 hover:bg-gray-500/15",
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function AlertsTable() {
  const { alerts, isLoading, error } = useAlerts();

  if (error) {
    return <p className="text-destructive text-sm">Failed to load alerts.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[100px]">Time</TableHead>
          <TableHead className="w-[120px]">Pair</TableHead>
          <TableHead>Exchange</TableHead>
          <TableHead className="w-[90px]">Category</TableHead>
          <TableHead>Signal</TableHead>
          <TableHead className="w-[80px] text-right">Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          : alerts.map((alert) => {
              const category = RULE_CATEGORY[alert.rule_name] ?? DEFAULT_CATEGORY;
              return (
                <TableRow key={alert.id}>
                  <TableCell
                    className="text-muted-foreground text-xs whitespace-nowrap"
                    title={new Date(alert.triggered_at).toLocaleString()}
                  >
                    {formatTimeAgo(alert.triggered_at)}
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold">{alert.symbol}</span>
                    <span className="text-muted-foreground text-xs ml-1.5">{alert.timeframe}</span>
                  </TableCell>
                  <TableCell className="capitalize">{alert.exchange_slug}</TableCell>
                  <TableCell>
                    <Badge className={category.className}>{category.label}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {alert.message}
                  </TableCell>
                  <TableCell className="text-right">
                    <AlertBadge sent={alert.sent} />
                  </TableCell>
                </TableRow>
              );
            })}
        {!isLoading && alerts.length === 0 && (
          <TableRow>
            <TableCell colSpan={6} className="text-center text-muted-foreground">
              No alerts yet.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
