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
import { TermTooltip } from "@/components/ui/term-tooltip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { Repository, RiskFile } from "@/lib/api/types";
import { formatDateTime, formatSnakeCase } from "@/lib/format";
import {
  useGetIndexStatusQuery,
  useGetRepositoryRiskQuery,
  useListRepositoriesQuery,
} from "@/store/api/gitvaneApi";

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
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col gap-5 border-b border-border/70 pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="mt-3 text-3xl font-extrabold tracking-tight md:text-4xl text-balance">
            GitVane Dashboard
          </h1>
          <p className="mt-2.5 max-w-3xl text-sm leading-relaxed text-muted font-medium text-balance">
            Just as a weather vane shows which way the wind blows, GitVane shows developers which way their Git changes and dependency impacts propagate.
          </p>
        </div>
        <Button asChild variant="primary">
          <Link href="/repositories">
            <GitBranch aria-hidden="true" className="size-4" />
            Add repository
          </Link>
        </Button>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
                {[1, 2, 3].map((id) => (
                  <div
                    className="grid gap-3 rounded-lg border border-border/60 bg-panel-muted px-4 py-3 md:grid-cols-[1fr_auto]"
                    key={`overview-repo-skeleton-${id}`}
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

      <section>
        <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-muted mb-3.5">
          Quick Workflows
        </h2>
        <div className="grid gap-3.5 md:grid-cols-2 xl:grid-cols-4">
          {quickActions.map((action) => (
            <Card
              className="group relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-glow"
              key={action.href}
            >
              <Link className="block p-5" href={action.href}>
                <div className="flex size-9 items-center justify-center rounded-lg border border-border/60 bg-panel-muted/80 text-muted transition-colors group-hover:border-primary/30 group-hover:bg-primary/10 group-hover:text-primary">
                  <action.icon aria-hidden="true" className="size-4" />
                </div>
                <p className="mt-4 text-sm font-bold tracking-tight text-foreground group-hover:text-primary transition-colors">
                  {action.label}
                </p>
                <p className="mt-2 font-mono text-[11px] text-muted/80 truncate">
                  {action.href}
                </p>
              </Link>
            </Card>
          ))}
        </div>
      </section>

      {firstRepository ? (
        <section className="grid gap-5 xl:grid-cols-2">
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

const OVERVIEW_METRIC_DESCRIPTIONS: Record<string, string> = {
  Repositories: "Total number of codebases registered in your GitVane account.",
  Indexed: "Number of repositories with fully processed architectural index databases.",
  Files: "Total source code files parsed across indexed repositories.",
  "Last indexed": "Timestamp of the most recently processed repository indexing run.",
};

function MetricCard({ label, value }: { label: string; value: string }) {
  const desc = OVERVIEW_METRIC_DESCRIPTIONS[label];

  return (
    <Card className="p-5 transition-all duration-200 hover:border-border hover:shadow-panel">
      <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted">
        {desc ? <TermTooltip description={desc} term={label} /> : label}
      </div>
      <p className="mt-3 truncate font-mono text-2xl font-extrabold tracking-tight tabular-nums text-foreground">
        {value}
      </p>
    </Card>
  );
}

function RecentRepositories({ repositories }: { repositories: Repository[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold tracking-tight">Recent repositories</h2>
            <p className="mt-1 text-xs text-muted">
              Your registered codebases and their latest index processing states.
            </p>
          </div>
          <span className="text-xs text-muted font-medium">
            {repositories.length} total
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2.5">
          {repositories.slice(0, 5).map((repository) => (
            <Link
              className="grid gap-3 rounded-lg border border-border/60 bg-panel-muted/50 px-4 py-3.5 text-sm transition-all duration-150 hover:border-primary/40 hover:bg-panel-muted md:grid-cols-[1fr_auto]"
              href={`/repositories/${repository.id}`}
              key={repository.id}
            >
              <span className="min-w-0">
                <span className="block truncate font-bold text-foreground">
                  {repository.name}
                </span>
                <span className="mt-1 block truncate font-mono text-xs text-muted">
                  {repository.last_indexed_commit ?? "No indexed commit"}
                </span>
              </span>
              <span className="flex flex-wrap items-center gap-2.5 md:justify-end">
                <Badge tone={repository.status === "indexed" ? "success" : "neutral"}>
                  {formatSnakeCase(repository.status)}
                </Badge>
                <span className="font-mono text-xs text-muted tabular-nums">
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
          <h2 className="text-sm font-bold tracking-tight">Risk summary</h2>
          <Link
            className="text-xs font-semibold text-primary hover:underline"
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
              <span className="font-mono text-xs font-semibold tabular-nums">
                {(highestRisk.risk_score * 100).toFixed(1)}%
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
            <p className="text-sm leading-relaxed text-muted">
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
          <h2 className="text-sm font-bold tracking-tight">Evaluation summary</h2>
          <span className="text-xs text-muted font-medium">Manual run</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted">
            Evaluation summaries are loaded by run ID. Open the evaluation dashboard to
            start a run or refresh an existing report.
          </p>
          <div className="rounded-lg border border-border/70 bg-panel-muted/60 px-3.5 py-2.5">
            <p className="text-xs text-muted">
              Evaluation results will appear after running an evaluation pipeline.
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
