"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { AlertCircle, FlaskConical, GitGraph, Filter, RefreshCw, ShieldAlert, Zap } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Label,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TermTooltip } from "@/components/ui/term-tooltip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";
import { normalizeApiError } from "@/lib/api/errors";
import type { RiskFile } from "@/lib/api/types";
import {
  useGetRepositoryQuery,
  useGetRepositoryRiskQuery,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

type RiskFilters = {
  includeTests: boolean;
  language: string;
  search: string;
  topK: number;
};

const defaultFilters: RiskFilters = {
  includeTests: false,
  language: "",
  search: "",
  topK: 20,
};

export function RiskDashboardPage({
  initialPath,
  repositoryId,
}: {
  initialPath?: string;
  repositoryId: string;
}) {
  const validRepositoryId = typeof repositoryId === "string" && repositoryId.trim() !== "" ? repositoryId : null;
  const searchParams = useSearchParams();
  const pathParam = initialPath ?? searchParams?.get("path") ?? searchParams?.get("search") ?? searchParams?.get("query") ?? "";

  const [draftFilters, setDraftFilters] = useState<RiskFilters>(() => ({
    ...defaultFilters,
    search: pathParam,
  }));
  const [appliedFilters, setAppliedFilters] = useState<RiskFilters>(() => ({
    ...defaultFilters,
    search: pathParam,
  }));
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const riskQueryArgs = validRepositoryId
    ? {
        include_tests: appliedFilters.includeTests,
        language: appliedFilters.language.trim() || null,
        repositoryId: validRepositoryId,
        top_k: appliedFilters.topK,
      }
    : skipToken;
  const risk = useGetRepositoryRiskQuery(riskQueryArgs);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  useEffect(() => {
    if (pathParam) {
      setDraftFilters((curr) => ({ ...curr, search: pathParam }));
      setAppliedFilters((curr) => ({ ...curr, search: pathParam }));
    }
  }, [pathParam]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedFilters({
      includeTests: draftFilters.includeTests,
      language: draftFilters.language.trim(),
      search: draftFilters.search.trim(),
      topK: Math.max(1, draftFilters.topK),
    });
  };

  const files = useMemo(() => {
    const rawFiles = risk.data?.files ?? [];
    if (!appliedFilters.search) return rawFiles;
    const query = appliedFilters.search.toLowerCase();
    return rawFiles.filter((file) => file.path.toLowerCase().includes(query));
  }, [risk.data?.files, appliedFilters.search]);

  const error = risk.error ? normalizeApiError(risk.error).message : null;
  const chartData = useMemo(() => buildRiskBuckets(files), [files]);
  const topComponents = useMemo(() => summarizeComponents(files), [files]);

  if (!validRepositoryId) {
    return (
      <EmptyState
        description="The repository identifier in the route is not valid."
        title="Repository not found"
      />
    );
  }

  if (repository.error) {
    return (
      <EmptyState
        action={
          <Button onClick={() => void repository.refetch()} type="button">
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </Button>
        }
        description={normalizeApiError(repository.error).message}
        icon={<AlertCircle aria-hidden="true" className="size-5" />}
        title="Repository not found"
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="warning">Risk</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Risk ranking</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
            Identify high-risk files in your codebase calculated from change frequency (churn),
            cyclomatic complexity, and structural dependency connections (fan-in / fan-out).
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Filters</h2>
              <p className="mt-1 text-xs text-muted">
                Filter repository files by risk threshold, path keywords, or result limits.
              </p>
            </div>
            <Badge>Heuristic score</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 lg:grid-cols-[140px_1fr_1fr_auto_auto]"
            onSubmit={handleSubmit}
          >
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="risk-top-k">
                Top files
              </label>
              <Input
                id="risk-top-k"
                max={200}
                min={1}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    topK: Number(event.target.value),
                  }))
                }
                type="number"
                value={draftFilters.topK}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="risk-search">
                File search
              </label>
              <Input
                id="risk-search"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    search: event.target.value,
                  }))
                }
                placeholder="e.g. src/auth/service.py"
                value={draftFilters.search}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="risk-language">
                Language filter
              </label>
              <Input
                id="risk-language"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    language: event.target.value,
                  }))
                }
                placeholder="e.g. python, typescript, go"
                value={draftFilters.language}
              />
            </div>
            <label className="flex h-9 items-center gap-2 self-end rounded-md border border-border bg-panel px-3 text-sm">
              <input
                checked={draftFilters.includeTests}
                className="size-4 rounded border-border text-primary focus:ring-primary"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    includeTests: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Include tests
            </label>
            <div className="flex gap-2 self-end">
              <Button disabled={risk.isFetching} type="submit" variant="primary">
                <Filter aria-hidden="true" className="size-4" />
                Apply
              </Button>
              <Button
                disabled={risk.isFetching}
                onClick={() => risk.refetch()}
                type="button"
              >
                <RefreshCw aria-hidden="true" className="size-4" />
                Refresh
              </Button>
            </div>
          </form>

          {error ? (
            <Notice className="mt-4" tone="danger">
              {error}
            </Notice>
          ) : null}
        </CardContent>
      </Card>

      {risk.isLoading ? (
        <RiskLoadingState />
      ) : files.length > 0 ? (
        <>
          <RiskSummary files={files} chartData={chartData} components={topComponents} />
          <RiskTable files={files} repositoryId={validRepositoryId} />
        </>
      ) : risk.isSuccess ? (
        <EmptyState
          description="No risk-ranked files found for these filters."
          icon={<ShieldAlert aria-hidden="true" className="size-5" />}
          title="No risk results"
        />
      ) : (
        <EmptyState
          description="Risk data will load once the repository metadata has been processed."
          icon={<ShieldAlert aria-hidden="true" className="size-5" />}
          title="Risk ranking"
        />
      )}
    </div>
  );
}

function buildRiskBuckets(files: RiskFile[]) {
  const buckets = [
    { count: 0, label: "0% - 25% (Low)" },
    { count: 0, label: "25% - 50% (Moderate)" },
    { count: 0, label: "50% - 75% (High)" },
    { count: 0, label: "75% - 100% (Critical)" },
  ];

  files.forEach((file) => {
    const score = Math.max(0, Math.min(1, file.risk_score));
    const index = Math.min(3, Math.floor(score * 4));
    buckets[index].count += 1;
  });

  return buckets;
}

function summarizeComponents(files: RiskFile[]) {
  const totals = new Map<string, number>();

  files.forEach((file) => {
    Object.entries(file.components).forEach(([name, value]) => {
      totals.set(name, (totals.get(name) ?? 0) + value);
    });
  });

  return Array.from(totals.entries())
    .map(([name, value]) => ({
      name,
      value: files.length > 0 ? value / files.length : 0,
    }))
    .sort((left, right) => right.value - left.value)
    .slice(0, 4);
}

function RiskLoadingState() {
  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card className="p-5">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-5 h-56 w-full" />
      </Card>
      <Card className="p-5">
        <Skeleton className="h-4 w-44" />
        <Skeleton className="mt-5 h-56 w-full" />
      </Card>
    </div>
  );
}

function RiskSummary({
  chartData,
  components,
  files,
}: {
  chartData: ReturnType<typeof buildRiskBuckets>;
  components: ReturnType<typeof summarizeComponents>;
  files: RiskFile[];
}) {
  const averageRisk =
    files.reduce((total, file) => total + file.risk_score, 0) / files.length;
  const highestRisk = files[0];

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk summary</h2>
          <p className="mt-1 text-xs text-muted">
            Overview of total file count, average risk score, and top architectural signal weights.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric
              description="Total number of repository source files included in this risk assessment."
              label="Files"
              value={String(files.length)}
            />
            <Metric
              description="Mean calculated risk percentage across all evaluated repository files."
              label="Average"
              value={`${(averageRisk * 100).toFixed(1)}%`}
            />
            <Metric
              description="Risk percentage of the most critical file identified in the current index."
              label="Highest"
              value={`${(highestRisk.risk_score * 100).toFixed(1)}%`}
            />
          </div>
          <div className="mt-5 space-y-3">
            <h3 className="text-sm font-semibold">Top component signals</h3>
            {components.length > 0 ? (
              components.map((component) => {
                const info = COMPONENT_DESCRIPTIONS[component.name] || {
                  label: component.name,
                  desc: `Average component signal weight for ${component.name}.`,
                };

                return (
                  <div className="space-y-1" key={component.name}>
                    <div className="flex justify-between gap-3 text-xs">
                      <TermTooltip description={info.desc} term={info.label} />
                      <span className="font-mono">{(component.value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 rounded-sm bg-panel-muted">
                      <div
                        className="h-2 rounded-sm bg-primary"
                        style={{ width: `${Math.min(100, component.value * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-muted">No component values returned.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk distribution</h2>
          <p className="mt-1 text-xs text-muted">
            Histogram grouping files into risk level percentage buckets (0% to 100%).
          </p>
        </CardHeader>
        <CardContent>
          <div className="h-64 min-w-0">
            <ResponsiveContainer height="100%" minWidth={300} width="100%">
              <BarChart
                data={chartData}
                margin={{ bottom: 20, left: 10, right: 10, top: 8 }}
              >
                <CartesianGrid stroke="rgb(var(--color-border))" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  fontSize={11}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                >
                  <Label
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    offset={-12}
                    position="insideBottom"
                    value="Risk Level Range (%)"
                  />
                </XAxis>
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  fontSize={11}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                >
                  <Label
                    angle={-90}
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    position="insideLeft"
                    style={{ textAnchor: "middle" }}
                    value="File Count"
                  />
                </YAxis>
                <Tooltip
                  contentStyle={{
                    background: "rgb(var(--color-panel))",
                    border: "1px solid rgb(var(--color-border))",
                    borderRadius: 8,
                    color: "rgb(var(--color-foreground))",
                  }}
                  cursor={{ fill: "rgb(var(--color-panel-muted))" }}
                />
                <Bar
                  barSize={36}
                  dataKey="count"
                  fill="rgb(var(--color-chart-b))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function RiskTable({
  files,
  repositoryId,
}: {
  files: RiskFile[];
  repositoryId: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-sm font-semibold">Ranked files</h2>
            <p className="mt-1 text-xs text-muted">
              Source files ordered by calculated risk score with detailed component breakdowns.
            </p>
          </div>
          <Badge>{files.length} files</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell className="w-16">Rank</TableHeaderCell>
              <TableHeaderCell>File</TableHeaderCell>
              <TableHeaderCell className="w-24 text-right">Risk</TableHeaderCell>
              <TableHeaderCell>Components</TableHeaderCell>
              <TableHeaderCell>Actions</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {files.map((file, index) => (
              <TableRow key={file.path}>
                <TableCell className="font-mono text-xs text-muted">
                  #{index + 1}
                </TableCell>
                <TableCell>
                  <div>
                    <span className="break-all font-mono text-sm font-semibold">
                      {file.path}
                    </span>
                    {file.reasons && file.reasons.length > 0 ? (
                      <ul className="mt-1 space-y-0.5 text-xs text-muted">
                        {file.reasons.map((reason) => (
                          <li key={reason}>• {reason}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {(file.risk_score * 100).toFixed(1)}%
                </TableCell>
                <TableCell>
                  <ComponentDetails components={file.components} />
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/impact?path=${encodeURIComponent(file.path)}`}
                      >
                        <Zap aria-hidden="true" className="size-3.5" />
                        Impact
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/graph?path=${encodeURIComponent(file.path)}`}
                      >
                        <GitGraph aria-hidden="true" className="size-3.5" />
                        Graph
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/tests?path=${encodeURIComponent(file.path)}`}
                      >
                        <FlaskConical aria-hidden="true" className="size-3.5" />
                        Tests
                      </Link>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

const COMPONENT_DESCRIPTIONS: Record<string, { label: string; desc: string }> = {
  fan_in: {
    label: "fan_in",
    desc: "Number of incoming dependencies (other modules that import this file). High fan-in indicates wide impact if modified.",
  },
  fan_out: {
    label: "fan_out",
    desc: "Number of outgoing dependencies (modules imported by this file). High fan-out makes this file sensitive to external changes.",
  },
  centrality: {
    label: "centrality",
    desc: "Graph centrality score measuring how critical this node is as an architectural hub connecting multiple components.",
  },
  complexity: {
    label: "complexity",
    desc: "Cyclomatic decision pathway complexity. Highly complex control flows are prone to subtle bugs.",
  },
  churn: {
    label: "churn",
    desc: "Recent file modification frequency. Frequently edited files have a higher likelihood of regression.",
  },
  dependency: {
    label: "dependency",
    desc: "Structural coupling strength in the repository dependency graph.",
  },
  risk: {
    label: "risk",
    desc: "Overall heuristic risk score combining structural metrics and churn history.",
  },
};

function ComponentDetails({ components }: { components: Record<string, number> }) {
  const entries = Object.entries(components).sort((left, right) => right[1] - left[1]);

  if (entries.length === 0) {
    return <span className="text-sm text-muted">No components</span>;
  }

  return (
    <div className="min-w-44 space-y-2">
      {entries.map(([name, value]) => {
        const info = COMPONENT_DESCRIPTIONS[name] || {
          label: name,
          desc: `Architectural signal weight for ${name}.`,
        };

        return (
          <div className="space-y-1" key={name}>
            <div className="flex justify-between gap-3 text-xs">
              <TermTooltip description={info.desc} term={info.label} />
              <span className="font-mono">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 rounded-sm bg-panel-muted">
              <div
                className="h-1.5 rounded-sm bg-primary"
                style={{ width: `${Math.min(100, Math.max(0, value) * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Metric({
  description,
  label,
  value,
}: {
  description?: string;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {description ? <TermTooltip description={description} term={label} /> : label}
      </div>
      <div className="mt-1 font-mono text-lg font-semibold">{value}</div>
    </div>
  );
}
