import { PageShell } from "@/components/layout/PageShell";
import { AlertsTable } from "@/components/alerts/AlertsTable";

export default function AlertsPage() {
  return (
    <PageShell title="Alert History">
      <AlertsTable />
    </PageShell>
  );
}
