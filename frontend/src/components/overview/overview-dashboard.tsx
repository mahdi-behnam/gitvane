"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import {
  ArrowRight,
  BarChart3,
  FlaskConical,
  GitBranch,
  GitGraph,
  Play,
  Search,
  Server,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { Repository } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import {
  useGetHealthQuery,
  useGetIndexStatusQuery,
  useListRepositoriesQuery,
} from "@/store/api/repolensApi";

export function OverviewDashboard() {
  const repositories = useListRepositoriesQuery();
  const health = useGetHealthQuery();
  const repositoryItems = repositories.data?.items ?? [];
  const firstRepository = repositoryItems[0];
  const indexStatus = useGetIndexStatusQuery(firstRepository?.id ?? skipToken);
  const repositoryScopedHref = firstRepository
    ? `/repositories/${firstRepository.id}`
    : "/repositories";
  const repositoryError = repositories.error
    ? normalizeApiError(repositories.error).message
    : null;

  const indexedRepositories = repositoryItems.filter(
    (repository) => repository.status === "indexed",
  ).length;
  const latestIndexedRepository = repositoryItems.find(
    (repository) => repository.indexed_at,
  );
  const quickActions = buildQuickActions(repositoryScopedHref);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Overview</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            RepoLens dashboard
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Register repositories, inspect indexing state, and choose the next analysis
            workflow.
          </p>
        </div>
        <Button asChild variant="primary">
          <Link href="/repositories">
            <GitBranch aria-hidden="true" className="size-4" />
            Add repository
          </Link>
        </Button>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Repositories"
          value={String(repositories.data?.total ?? 0)}
        />
        <MetricCard label="Indexed" value={String(indexedRepositories)} />
        <MetricCard
          label="Files"
          value={indexStatus.data ? String(indexStatus.data.file_count) : "0"}
        />
        <MetricCard
          label="Last indexed"
          value={formatDateTime(latestIndexedRepository?.indexed_at ?? null)}
        />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        {repositories.isLoading ? (
          <Card className="p-8">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="mt-4 h-4 w-2/3" />
            <Skeleton className="mt-6 h-24 w-full" />
          </Card>
        ) : repositoryError ? (
          <EmptyState
            description={repositoryError}
            icon={<Search aria-hidden="true" className="size-5" />}
            title="Repository summary unavailable"
          />
        ) : repositories.data?.items.length === 0 ? (
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
        ) : (
          <RecentRepositories repositories={repositoryItems} />
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Backend status</h2>
              <Badge tone={health.data?.status === "healthy" ? "success" : "neutral"}>
                {health.isLoading
                  ? "Checking"
                  : health.data?.status === "healthy"
                    ? "Healthy"
                    : "Manual"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4 text-sm">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Repositories</dt>
                <dd className="font-semibold">{repositories.data?.total ?? 0}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Indexed files</dt>
                <dd className="font-semibold">{indexStatus.data?.file_count ?? 0}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Symbols</dt>
                <dd className="font-semibold">{indexStatus.data?.symbol_count ?? 0}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Database</dt>
                <dd className="font-mono text-xs text-muted">
                  {health.data?.database ?? "Unknown"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {quickActions.map((action) => (
          <Card className="transition hover:bg-panel-muted" key={action.href}>
            <Link className="block p-5" href={action.href}>
              <action.icon aria-hidden="true" className="size-4 text-muted" />
              <p className="mt-4 text-sm font-medium">{action.label}</p>
              <p className="mt-3 font-mono text-xs text-muted">{action.href}</p>
            </Link>
          </Card>
        ))}
      </section>
    </div>
  );
}

function buildQuickActions(repositoryScopedHref: string) {
  return [
    { href: "/repositories", icon: GitBranch, label: "Add repository" },
    {
      href: `${repositoryScopedHref}/search`,
      icon: Search,
      label: "Run semantic search",
    },
    {
      href: `${repositoryScopedHref}/impact`,
      icon: Play,
      label: "Analyze impact",
    },
    {
      href: `${repositoryScopedHref}/graph`,
      icon: GitGraph,
      label: "Open graph",
    },
    {
      href: `${repositoryScopedHref}/risk`,
      icon: Server,
      label: "Review risk",
    },
    {
      href: `${repositoryScopedHref}/tests`,
      icon: FlaskConical,
      label: "Recommend tests",
    },
    {
      href: `${repositoryScopedHref}/evaluation`,
      icon: BarChart3,
      label: "Open evaluation",
    },
  ];
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {label}
      </p>
      <p className="mt-2 truncate font-mono text-lg font-semibold">{value}</p>
    </Card>
  );
}

function RecentRepositories({ repositories }: { repositories: Repository[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Recent repositories</h2>
          <Badge>{repositories.length} total</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {repositories.slice(0, 5).map((repository) => (
            <Link
              className="grid gap-3 rounded-md border border-border bg-panel-muted px-3 py-3 text-sm md:grid-cols-[1fr_auto]"
              href={`/repositories/${repository.id}`}
              key={repository.id}
            >
              <span className="min-w-0">
                <span className="block truncate font-medium">{repository.name}</span>
                <span className="mt-1 block truncate font-mono text-xs text-muted">
                  {repository.last_indexed_commit ?? "No indexed commit"}
                </span>
              </span>
              <span className="flex flex-wrap items-center gap-2 md:justify-end">
                <Badge tone={repository.status === "indexed" ? "success" : "neutral"}>
                  {repository.status}
                </Badge>
                <span className="font-mono text-xs text-muted">
                  {formatDateTime(repository.indexed_at)}
                </span>
              </span>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
