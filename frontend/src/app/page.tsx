import { PageShell } from "@/components/layout/PageShell";
import { PairsList } from "@/components/pairs/PairsList";

export default function DashboardPage() {
  return (
    <PageShell title="Dashboard">
      <PairsList />
    </PageShell>
  );
}
