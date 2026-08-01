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
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { Repository, RiskFile } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import {
  useGetIndexStatusQuery,
  useGetRepositoryRiskQuery,
  useListRepositoriesQuery,
} from "@/store/api/repolensApi";

export function OverviewDashboard() {
  const repositories = useListRepositoriesQuery();
  const repositoryItems = repositories.data?.items ?? [];
  const firstRepository = repositoryItems[0];
  const indexStatus = useGetIndexStatusQuery(firstRepository?.id ?? skipToken);
  const risk = useGetRepositoryRiskQuery(
    firstRepository
      ? { include_tests: false, repositoryId: firstRepository.id, top_k: 3 }
      : skipToken,
  );
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

      <div>
        {repositories.isLoading ? (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-5 w-16" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div
                    className="grid gap-3 rounded-md border border-border bg-panel-muted px-3 py-3 md:grid-cols-[1fr_auto]"
                    key={index}
                  >
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-40" />
                      <Skeleton className="h-3 w-28" />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 md:justify-end">
                      <Skeleton className="h-5 w-16" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
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

      {firstRepository ? (
        <section className="grid gap-4 xl:grid-cols-2">
          <RiskInsightCard
            error={risk.error ? normalizeApiError(risk.error).message : null}
            files={risk.data?.files ?? []}
            isLoading={risk.isLoading}
            repositoryId={firstRepository.id}
          />
          <EvaluationInsightCard repositoryId={firstRepository.id} />
        </section>
      ) : null}
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

function RiskInsightCard({
  error,
  files,
  isLoading,
  repositoryId,
}: {
  error: string | null;
  files: RiskFile[];
  isLoading: boolean;
  repositoryId: string;
}) {
  const highestRisk = files[0];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Risk summary</h2>
          <Link
            className="text-xs text-primary hover:underline"
            href={`/repositories/${repositoryId}/risk`}
          >
            View details
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-12" />
            </div>
            <Skeleton className="h-8 w-24" />
          </div>
        ) : error ? (
          <Notice tone="danger">{error}</Notice>
        ) : highestRisk ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs text-muted truncate">
                {highestRisk.path}
              </span>
              <span className="font-mono text-xs font-semibold">
                {highestRisk.risk_score.toFixed(2)}
              </span>
            </div>
            <Button asChild size="sm">
              <Link href={`/repositories/${repositoryId}/risk`}>
                <ShieldAlert aria-hidden="true" className="size-4" />
                Open risk
              </Link>
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm leading-6 text-muted">
              Risk data appears after the repository has indexed file metadata.
            </p>
            <Button asChild size="sm">
              <Link href={`/repositories/${repositoryId}/risk`}>
                <ShieldAlert aria-hidden="true" className="size-4" />
                Open risk
              </Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EvaluationInsightCard({ repositoryId }: { repositoryId: string }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Evaluation summary</h2>
          <Badge tone="neutral">Manual run</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm leading-6 text-muted">
            Evaluation summaries are loaded by run ID. Open the evaluation dashboard to
            start a run or refresh an existing report.
          </p>
          <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
              Current backend surface
            </p>
            <p className="mt-2 text-sm text-muted">
              No latest-run endpoint is available, so this card does not invent
              evaluation results.
            </p>
          </div>
          <Button asChild size="sm">
            <Link href={`/repositories/${repositoryId}/evaluation`}>
              <BarChart3 aria-hidden="true" className="size-4" />
              Open evaluation
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
