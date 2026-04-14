import Link from "next/link";

export function Navbar() {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Candle
        </Link>
        <nav className="flex gap-4 text-sm text-muted-foreground">
          <Link href="/" className="hover:text-foreground transition-colors">
            Pairs
          </Link>
          <Link href="/alerts" className="hover:text-foreground transition-colors">
            Alerts
          </Link>
        </nav>
      </div>
    </header>
  );
}
