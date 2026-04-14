import { PageShell } from "@/components/layout/PageShell";
import { CandleChart } from "@/components/chart/CandleChart";
import { getPairs } from "@/lib/api";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function PairPage({ params }: Props) {
  const { id } = await params;
  const pairId = Number(id);

  const { pairs } = await getPairs();
  const pair = pairs.find((p) => p.id === pairId);

  const title = pair ? `${pair.symbol} · ${pair.timeframe}` : `Pair #${id}`;

  return (
    <PageShell title={title}>
      <CandleChart pairId={pairId} />
    </PageShell>
  );
}
