"use client";

import { usePairs } from "@/hooks/usePairs";
import { PairCard } from "./PairCard";
import { Skeleton } from "@/components/ui/skeleton";

export function PairsList() {
  const { pairs, isLoading, error } = usePairs();

  if (error) {
    return <p className="text-destructive text-sm">Failed to load pairs.</p>;
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    );
  }

  if (pairs.length === 0) {
    return <p className="text-muted-foreground text-sm">No active pairs found.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {pairs.map((pair) => (
        <PairCard key={pair.id} pair={pair} />
      ))}
    </div>
  );
}
