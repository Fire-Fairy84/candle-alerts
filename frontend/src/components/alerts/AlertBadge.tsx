import { Badge } from "@/components/ui/badge";

export function AlertBadge({ sent }: { sent: boolean }) {
  return sent ? (
    <Badge className="bg-green-500/15 text-green-500 hover:bg-green-500/15">Sent</Badge>
  ) : (
    <Badge className="bg-yellow-500/15 text-yellow-500 hover:bg-yellow-500/15">Pending</Badge>
  );
}
