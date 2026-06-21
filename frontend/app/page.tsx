import { ArrowRight, GitBranch, Search } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

const quickActions = [
  { href: "/repositories", label: "Add repository" },
  { href: "/repositories/current/search", label: "Run semantic search" },
  { href: "/repositories/current/impact", label: "Analyze impact" },
  { href: "/repositories/current/graph", label: "Open graph" },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Overview</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            RepoLens dashboard
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Repository intelligence will appear here as backend data is connected.
          </p>
        </div>
        <Button asChild variant="primary">
          <Link href="/repositories">
            <GitBranch aria-hidden="true" className="size-4" />
            Add repository
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <EmptyState
          action={
            <Button asChild>
              <Link href="/repositories">
                Open repositories
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </Button>
          }
          description="Register a repository to begin indexing, searching, and tracing likely change impact."
          icon={<Search aria-hidden="true" className="size-5" />}
          title="No repositories registered"
        />

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Backend status</h2>
              <Badge>Manual refresh</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Skeleton className="h-3 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-3 w-5/6" />
            </div>
          </CardContent>
        </Card>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {quickActions.map((action) => (
          <Card className="transition hover:bg-panel-muted" key={action.href}>
            <Link className="block p-5" href={action.href}>
              <p className="text-sm font-medium">{action.label}</p>
              <p className="mt-3 font-mono text-xs text-muted">{action.href}</p>
            </Link>
          </Card>
        ))}
      </section>
    </div>
  );
}
